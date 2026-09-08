@echo off
cd /d "C:\Users\DELL\Documents\GitHub\J-549-azhan-branch"

:loop
git add .
git commit -m "completed"
git push

timeout /t 5
goto loop