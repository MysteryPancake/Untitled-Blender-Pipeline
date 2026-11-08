"""
Headless asset build, run through `build.bat` or directly:\n
    blender -b --factory-startup -P build_cli.py -- --asset NAME --database PATH
"""
import argparse, importlib, os, sys

import bpy

def get_args() -> argparse.Namespace:
	"""Gets arguments after the `--` Blender leaves for scripts"""
	argv = sys.argv
	script_args = argv[argv.index("--") + 1:] if "--" in argv else []
	parser = argparse.ArgumentParser(prog="build_cli.py")
	parser.add_argument("-a", "--asset", required=True, help="Asset name to build")
	parser.add_argument("-d", "--database", help="Database folder (defaults to the SG_DATABASE environment variable)")
	return parser.parse_args(script_args)

def main() -> None:
	args = get_args()
	if args.database:
		os.environ["SG_DATABASE"] = args.database

	# Import this folder as a package so the relative imports work
	package_dir = os.path.dirname(os.path.abspath(__file__))
	sys.path.insert(0, os.path.dirname(package_dir))
	package = importlib.import_module(os.path.basename(package_dir))

	# Start from an empty file
	bpy.ops.wm.read_factory_settings(use_empty=True)

	package.build.run_build(args.asset)

if __name__ == "__main__":
	main()
