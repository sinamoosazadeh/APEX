#!/data/data/com.termux/files/usr/bin/bash
# Termux:Boot entry - place in ~/.termux/boot/ to start APEX on device
# boot (Book II 29.20 service lifecycle). Requires the Termux:Boot app.
termux-wake-lock 2>/dev/null || true
nohup bash "$HOME/APEX/deploy/termux/apex-service.sh" \
  >> "$HOME/APEX/runtime/service.log" 2>&1 &
