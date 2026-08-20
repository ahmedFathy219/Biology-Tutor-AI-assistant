# display_factory.py

import os
import platform
def create_display():
    """
    Create the appropriate display based on platform.
    Returns TftDisplay instance (either simulator or hardware).
    """
    
    # Check if running on Raspberry pi
    is_pi5 = False
    try:
        with open("/proc/device-tree/model", "r") as f:
            model = f.read().strip()
            if "Raspberry Pi 5" in model:
                is_pi5 = True
    except:
        pass
    if is_pi5:
        try:
            print("on raspberry ppppi 5")
            # Try to use hardware display
            from .st7735_display import TftDisplay
            display = TftDisplay()
            
            # Test initialization
            if display.start():
                print("Using hardware ST7735 display")
                return display
            else:
                print("Hardware display failed, falling back to simulator")
        except ImportError as e:
            print("Hardware display libraries not available, using simulator")
            print(f"[ERROR] : {e}")
    
    # Fall back to simulator
    from .tftDisplay import TftDisplay as SimulatorDisplay
    print("Using simulator display")
    return SimulatorDisplay()