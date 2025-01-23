autoFlask - Game UI Bar Detection and Analysis Tool
autoFlask is a Python-based utility for monitoring and analyzing dynamic game UI elements, such as health (HP) and mana bars, using RGB and ROI brightness calculations. The tool provides real-time percentage readings of bar states and enables automated actions or detailed data logging for further analysis.

Features:
RGB Brightness Analysis: Utilizes pixel brightness and RGB channel dominance to accurately detect changes in game bars, reducing noise and interference from overlapping visuals.
Customizable ROIs: Easily define regions of interest (ROIs) to target specific areas of the screen for health, mana, or other bar elements.
Real-Time Processing: Continuously monitors and updates bar states with precision, ideal for automation or strategic feedback.
Debugging Visuals: Generates histograms, heatmaps, and logs for pixel dominance and brightness, aiding in customization and debugging.
Lightweight Design: Optimized for performance, ensuring minimal resource usage during gameplay.

How It Works:
Define ROIs: Use intuitive start and end coordinate selection to identify the exact location of bars in the game UI.
Analyze RGB and Brightness: Extracts pixel data from the selected ROI, focusing on RGB brightness thresholds for red (HP) and blue (mana) channels.
Percentage Calculation: Applies smoothing filters and brightness thresholds to deliver consistent and accurate bar percentages.
Live Feedback: Outputs live data (HP: 100%, Mana: 72%) and supports triggers for predefined thresholds.

Use Cases:
Game Automation: Automate tasks such as healing or skill activation based on HP/mana percentages.
Performance Insights: Analyze bar changes for strategic gameplay or to study in-game mechanics.
Enhanced User Interface: Augment gameplay streams with live bar statistics for audience engagement.
Custom Integrations: Easily extend functionality with external automation scripts or tools.

Disclaimer:
This tool is intended for personal and educational use only. Any use in multiplayer games or in violation of game terms of service is not encouraged and may result in penalties. The user assumes full responsibility for compliance with applicable laws and regulations.
