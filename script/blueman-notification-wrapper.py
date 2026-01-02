#!/usr/bin/env python3
"""
Blueman Notification Icon Fixer
Intercepts D-Bus notifications from blueman and ensures bluetooth icon is preserved
"""

import dbus
import dbus.service
from dbus.mainloop.glib import DBusGMainLoop
from gi.repository import GLib

DBusGMainLoop(set_as_default=True)

class NotificationProxy(dbus.service.Object):
    """Proxy that forwards notifications to the real notification daemon"""
    
    def __init__(self):
        bus = dbus.SessionBus()
        bus_name = dbus.service.BusName('org.freedesktop.Notifications.Proxy', bus)
        dbus.service.Object.__init__(self, bus_name, '/org/freedesktop/Notifications')
        self.real_notifications = bus.get_object('org.freedesktop.Notifications',
                                                  '/org/freedesktop/Notifications')
        
    @dbus.service.method('org.freedesktop.Notifications',
                         in_signature='susssasa{sv}i', out_signature='u')
    def Notify(self, app_name, replaces_id, app_icon, summary, body, actions, hints, expire_timeout):
        """Intercept and modify notifications from blueman"""
        
        # If it's from blueman and uses "battery" icon, change it to bluetooth
        if app_name in ['blueman', 'blueman-applet'] and app_icon == 'battery':
            print(f"[Fix] Changing icon from 'battery' to 'bluetooth' for: {summary}")
            app_icon = 'bluetooth'
        
        # Forward to real notification daemon
        return self.real_notifications.Notify(
            app_name, replaces_id, app_icon, summary, body,
            actions, hints, expire_timeout
        )

if __name__ == '__main__':
    try:
        print("Starting Blueman Notification Icon Fixer...")
        proxy = NotificationProxy()
        loop = GLib.MainLoop()
        print("Monitoring blueman notifications...")
        loop.run()
    except KeyboardInterrupt:
        print("\nStopped")
    except Exception as e:
        print(f"Error: {e}")

