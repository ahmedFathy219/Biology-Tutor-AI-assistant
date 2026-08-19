# display_factory.py

import os
import sys

def create_display():
    """
    Create the appropriate display based on platform.
    Returns TftDisplay instance (either simulator or hardware).
    """
    
    # Check if running on Raspberry Pi
    if os.uname().sysname == 'Linux' and os.uname().machine.startswith('arm'):
        try:
            # Try to use hardware display
            from st7735_display import TftDisplay
            display = TftDisplay()
            
            # Test initialization
            if display.start():
                print("Using hardware ST7735 display")
                return display
            else:
                print("Hardware display failed, falling back to simulator")
        except ImportError:
            print("Hardware display libraries not available, using simulator")
    
    # Fall back to simulator
    from .tftDisplay import TftDisplay as SimulatorDisplay
    print("Using simulator display")
    return SimulatorDisplay()