import cv2
import numpy as np
import pyautogui
from collections import deque
import threading
import time


class FastBarMonitor:
    def __init__(self, log_callback=None):
        self.hp_coords = None
        self.mana_coords = None
        self.hp_reference_pixels = 1000  # Default fallback value
        self.mana_reference_pixels = 1000  # Default fallback value
        self.hp_threshold = 80
        self.mana_threshold = 80
        self.hp_key = "1"
        self.mana_key = "2"
        self.hp_buffer = deque(maxlen=10)  # Buffer for smoothing HP readings
        self.mana_buffer = deque(maxlen=10)  # Buffer for smoothing Mana readings
        self.monitoring = False
        self.stop_event = threading.Event()
        self.log_callback = log_callback
        self.previous_hp_percentage = 100
        self.previous_mana_percentage = 100
        self.poll_interval = 0.15
        self.debug_logging = False
        self.aura_coords = None
        self.aura_monitoring = False
        self.aura_stop_event = threading.Event()
        self.aura_click_interval = 1.0
        self.aura_click_offset = 12

    def log(self, message):
        """Log messages to both the UI log window and the console."""
        if self.log_callback:
            self.log_callback(message)
        print(message)

    def debug_log(self, message):
        if self.debug_logging:
            self.log(message)

    def create_color_mask(self, roi, color):
        """
        Convert BGR -> HSV, log means, apply inRange for 'red' or 'blue',
        and save the mask for debugging.  (Same logic you already have.)
        """
        roi_hsv = cv2.cvtColor(roi, cv2.COLOR_BGR2HSV)
        H, S, V = cv2.split(roi_hsv)

        # Debug log
        h_mean, s_mean, v_mean = np.mean(H), np.mean(S), np.mean(V)
        self.debug_log(f"{color.capitalize()} HSV Means - H: {h_mean:.1f}, "
                       f"S: {s_mean:.1f}, V: {v_mean:.1f}")

        # Example broad ranges for 'blue' and 'red'
        if color == "blue":
            lower_blue1 = (0,   50,  40)   # catch "low hue" blue
            upper_blue1 = (30, 255, 255)
            lower_blue2 = (90,  50,  40)   # typical strong blue
            upper_blue2 = (140,255, 255)
            mask1 = cv2.inRange(roi_hsv, lower_blue1, upper_blue1)
            mask2 = cv2.inRange(roi_hsv, lower_blue2, upper_blue2)
            color_mask = cv2.bitwise_or(mask1, mask2)

        elif color == "red":
            # Notice we're including a range around H=120 if your "red" is actually that hue
            # but typically red is near 0-15 or 160-180. 
            # If your bar is near H~121, you might want to expand or shift the ranges:
            lower_red1 = (0,   70,  50)  
            upper_red1 = (15, 255, 255)
            lower_red2 = (110, 70,  40)  # expanded to catch H=120ish
            upper_red2 = (130, 255, 255)

            mask1 = cv2.inRange(roi_hsv, lower_red1, upper_red1)
            mask2 = cv2.inRange(roi_hsv, lower_red2, upper_red2)
            color_mask = cv2.bitwise_or(mask1, mask2)
        else:
            self.log(f"Unsupported color: {color}")
            return None

        return color_mask

    def capture_roi(self, coords, screenshot=None):
        """Capture the ROI and optionally save for debugging."""
        if not coords or coords[0] == coords[2] or coords[1] == coords[3]:
            self.log("Error: Invalid coordinates. Please set the bar positions again.")
            return None

        if screenshot is None:
            screenshot = pyautogui.screenshot()
        roi = np.array(screenshot.crop(coords))

        if roi.size == 0:
            self.log("Error: Captured ROI is empty. Check your bar coordinates.")
            return None

        roi = cv2.resize(roi, (100, 10))  # standardize size

        return roi

    def calculate_dominance(self, roi, color):
        """
        New approach: ratio-based dominance.
        - For 'blue': (Blue + 1) / (Red + Green + 1)
        - For 'red':  (Red + 1)  / (Green + Blue + 1)
        """
        roi_rgb = cv2.cvtColor(roi, cv2.COLOR_BGR2RGB)
        blue_channel = roi_rgb[:, :, 2].astype(np.float32)
        red_channel  = roi_rgb[:, :, 0].astype(np.float32)
        green_channel = roi_rgb[:, :, 1].astype(np.float32)

        if color == "blue":
            # Blue ratio => more blue relative to red+green
            dominance = (blue_channel + 1.0) / (red_channel + green_channel + 1.0)
            self.debug_log(f"Blue Ratio - Max: {np.max(dominance):.3f}, Min: {np.min(dominance):.3f}, Mean: {np.mean(dominance):.3f}")
        elif color == "red":
            # Red ratio => more red relative to green+blue
            dominance = (red_channel + 1.0) / (green_channel + blue_channel + 1.0)
            self.debug_log(f"Red Ratio - Max: {np.max(dominance):.3f}, Min: {np.min(dominance):.3f}, Mean: {np.mean(dominance):.3f}")
        else:
            raise ValueError("Unsupported color")

        # No more 'correction' constant subtraction; ratio itself is enough.
        return dominance

    def smooth_percentage(self, new_value, buffer):
        if not buffer:
            buffer.append(new_value)
            return new_value

        old_value = buffer[-1]
        diff = abs(new_value - old_value)

        # If it's a large jump, use smaller smoothing (faster update)
        if diff > 10:
            alpha = 0.3
        else:
            alpha = 0.1

        smoothed_value = (1 - alpha) * old_value + alpha * new_value
        buffer.append(smoothed_value)
        return smoothed_value

    def calculate_reference(self, roi, color):
        """
        Count how many pixels pass the mask. That's our 'full bar' reference.
        """
        color_mask = self.create_color_mask(roi, color)
        if color_mask is None:
            return 0

        filled_pixels = np.count_nonzero(color_mask)
        self.log(f"{color.capitalize()} Mask - Filled Pixels: {filled_pixels}")

        if filled_pixels <= 0:
            self.log(f"Warning: No valid '{color}' pixels detected.")
            return 0

        return filled_pixels

    def calculate_percentage(self, roi, color, reference_pixels, buffer):
        """Count masked pixels, compare to reference, get % fill, smooth it."""
        if reference_pixels <= 0:
            self.log(f"Error: Reference pixels for '{color}' invalid (<= 0).")
            return 0

        color_mask = self.create_color_mask(roi, color)
        if color_mask is None:
            return 0

        filled_pixels = np.count_nonzero(color_mask)

        # If it's below some minimal count, treat as empty or mismatch
        if filled_pixels < 0.005 * roi.size:
            self.log("Warning: Insufficient bar pixels detected. Possibly empty or ROI mismatch.")
            return 0

        percentage = (filled_pixels / reference_pixels) * 100
        percentage = max(0, min(100, percentage))
        smoothed_percentage = self.smooth_percentage(percentage, buffer)

        self.debug_log(f"{color.capitalize()} Mask - Current Pixels: {filled_pixels}, "
                       f"Reference: {reference_pixels}, Smoothed %: {smoothed_percentage:.2f}%")
        return smoothed_percentage

    def set_hp_bar(self):
        """
        Call this with HP bar truly full in-game. 
        We capture an ROI, get the reference from 'red' mask. 
        If valid, store it. If not, fallback.
        """
        self.log("Setting up HP bar. Ensure HP is 100% in-game.")
        self.hp_coords = self.get_coords("HP")
        if self.hp_coords:
            roi = self.capture_roi(self.hp_coords)
            if roi is not None:
                ref_pixels = self.calculate_reference(roi, "red")
                if ref_pixels <= 0:
                    self.log("HP reference detection failed -> fallback 100.")
                    ref_pixels = 100
                self.hp_reference_pixels = ref_pixels
                self.log(f"HP bar reference set: {ref_pixels} pixels.")

    def set_mana_bar(self):
        self.log("Setting up Mana bar. Make sure Mana is 100% in-game.")
        self.mana_coords = self.get_coords("Mana")
        if self.mana_coords:
            roi = self.capture_roi(self.mana_coords)
            if roi is not None:
                ref_pixels = self.calculate_reference(roi, "blue")
                if ref_pixels <= 0:
                    # Something went wrong; fallback
                    ref_pixels = 100
                    self.log("Mana reference detection failed -> fallback 100.")
                # Store the actual reference
                self.mana_reference_pixels = ref_pixels
                self.log(f"Mana bar reference set: {ref_pixels} pixels.")


    def get_coords(self, bar_type):
        """Capture coordinates for the specified bar type."""
        self.log(f"Capture {bar_type} coordinates with F2 (start) and F3 (end).")
        coords = []

        def on_f2():
            x1, y1 = pyautogui.position()
            coords.append((x1, y1))
            self.log(f"{bar_type} Start Point: {x1}, {y1}")

        def on_f3():
            x2, y2 = pyautogui.position()
            coords.append((x2, y2))
            self.log(f"{bar_type} End Point: {x2}, {y2}")

        return on_f2, on_f3, coords

    def start_monitoring(self):
        """Start monitoring the bars for changes in a loop until stop_event is triggered."""
        while not self.stop_event.is_set():
            log_output = ""
            screenshot = None

            if self.mana_coords or self.hp_coords:
                screenshot = pyautogui.screenshot()

            # Monitor Mana Bar
            if self.mana_coords:
                mana_roi = self.capture_roi(self.mana_coords, screenshot)
                if mana_roi is not None:
                    mana_percentage = self.calculate_percentage(
                        mana_roi, 
                        color="blue", 
                        reference_pixels=self.mana_reference_pixels, 
                        buffer=self.mana_buffer
                    )
                    # Check threshold logic (if mana < threshold, press key, etc.)
                    if mana_percentage < self.mana_threshold and self.previous_mana_percentage >= self.mana_threshold:
                        pyautogui.press(self.mana_key)
                        self.log(f"Mana Key '{self.mana_key}' pressed. "
                                f"Mana: {mana_percentage:.2f}%, "
                                f"Threshold: {self.mana_threshold}%")
                    self.previous_mana_percentage = mana_percentage
                    log_output += f"Mana: {mana_percentage:.2f}%\n"

            # Monitor HP Bar
            if self.hp_coords:
                hp_roi = self.capture_roi(self.hp_coords, screenshot)
                if hp_roi is not None:
                    hp_percentage = self.calculate_percentage(
                        hp_roi, 
                        color="red", 
                        reference_pixels=self.hp_reference_pixels, 
                        buffer=self.hp_buffer
                    )
                    # Check threshold logic (if hp < threshold, press key, etc.)
                    if hp_percentage < self.hp_threshold and self.previous_hp_percentage >= self.hp_threshold:
                        pyautogui.press(self.hp_key)
                        self.log(f"HP Key '{self.hp_key}' pressed. "
                                f"HP: {hp_percentage:.2f}%, "
                                f"Threshold: {self.hp_threshold}%")
                    self.previous_hp_percentage = hp_percentage
                    log_output += f"HP: {hp_percentage:.2f}%\n"

            # Output logs each iteration
            if log_output:
                self.debug_log(log_output.strip())

            time.sleep(self.poll_interval)  # small delay to avoid busy-wait


    def toggle_monitoring(self):
        """Toggle the monitoring state."""
        if self.monitoring:
            self.stop_event.set()
            self.monitoring = False
            self.log("Monitoring stopped.")
        else:
            self.stop_event.clear()
            monitoring_thread = threading.Thread(target=self.start_monitoring, daemon=True)
            monitoring_thread.start()
            self.monitoring = True
            self.log("Monitoring started.")
            
    def get_aura_click_point(self):
        if not self.aura_coords:
            return None

        x1, y1, x2, y2 = self.aura_coords
        click_x = int((x1 + x2) / 2)
        click_y = max(y1, y2) + self.aura_click_offset
        return click_x, click_y

    def start_aura_bot(self):
        while not self.aura_stop_event.is_set():
            click_point = self.get_aura_click_point()
            if not click_point:
                self.log("Aura bar is not set.")
                break

            pyautogui.click(*click_point, button="left")
            self.debug_log(f"Aura click at {click_point[0]}, {click_point[1]}")
            self.aura_stop_event.wait(self.aura_click_interval)

        self.aura_monitoring = False

    def toggle_aura_bot(self):
        if self.aura_monitoring:
            self.stop_aura_bot()
            return

        if not self.aura_coords:
            self.log("Set Aura bar before starting Aura Bot.")
            return

        self.aura_stop_event.clear()
        aura_thread = threading.Thread(target=self.start_aura_bot, daemon=True)
        aura_thread.start()
        self.aura_monitoring = True
        self.log("Aura Bot started.")

    def stop_aura_bot(self):
        if self.aura_monitoring:
            self.aura_stop_event.set()
            self.aura_monitoring = False
            self.log("Aura Bot stopped.")
    

