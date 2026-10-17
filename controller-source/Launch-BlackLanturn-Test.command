#!/bin/zsh
set -eu
TASK_ROOT="$(cd -- "$(dirname -- "$0")" && pwd)"
if ! KODI_PROCESS_LIST=$(/bin/ps -axo comm=); then
  print -u2 "Cannot check whether Kodi is running. The portable test will not start."
  exit 1
fi
if print -r -- "$KODI_PROCESS_LIST" | /usr/bin/grep -qE "/(Kodi|Kodi-Test|BlackLanturn-Test)\.app/Contents/MacOS/Kodi$"; then
  print "Quit Kodi normally first; the test uses a separate portable profile."
  exit 1
fi
if "$TASK_ROOT/BlackLanturn-Test.app/Contents/MacOS/Kodi" -p >"$TASK_ROOT/evidence/startup-console.log" 2>&1; then
  exit 0
else
  LAUNCH_STATUS=$?
  print -u2 "BlackLanturn Test exited with status $LAUNCH_STATUS. See $TASK_ROOT/evidence/startup-console.log."
  if [[ "$LAUNCH_STATUS" == 137 ]]; then
    print -u2 "macOS terminated the app. Inspect its code signature and macOS launch diagnostics before changing the skin or profile."
  fi
  exit "$LAUNCH_STATUS"
fi
