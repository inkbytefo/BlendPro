"""
UI module for BlendPro: AI Co-Pilot
Modern user interface components and panels
"""

from .main_panel import BLENDPRO_PT_MainPanel
from .chat_interface import ChatInterface, BLENDPRO_PT_ChatPanel
from .interactive_messages import InteractiveMessages, BLENDPRO_PT_InteractivePanel
from .settings_panel import BLENDPRO_PT_SettingsPanel, BLENDPROAddonPreferences

__all__ = [
    'BLENDPRO_PT_MainPanel',
    'ChatInterface',
    'BLENDPRO_PT_ChatPanel',
    'InteractiveMessages', 
    'BLENDPRO_PT_InteractivePanel',
    'BLENDPRO_PT_SettingsPanel',
    'BLENDPROAddonPreferences'
]
