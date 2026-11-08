:: Builds an asset headlessly from all of its layers
:: Set these as environment variables, or edit the defaults below
::   BLENDER_EXE - path to your blender.exe
::   SG_DATABASE - path to your database folder

@ECHO off

SETLOCAL
IF NOT DEFINED BLENDER_EXE SET "BLENDER_EXE=C:\Program Files (x86)\Steam\steamapps\common\Blender\blender.exe"
IF NOT DEFINED SG_DATABASE (
	ECHO SG_DATABASE isn't set. Point it at your database folder first.
	EXIT /B 1
)

SET /p asset="Type an asset name: "

"%BLENDER_EXE%" -b --factory-startup -P "%~dp0build_cli.py" -- --asset "%asset%" --database "%SG_DATABASE%"
ENDLOCAL