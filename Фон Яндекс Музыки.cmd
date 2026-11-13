@echo off
for %%f in ("%~dp0*.exe") do start "" "%%~ff"
