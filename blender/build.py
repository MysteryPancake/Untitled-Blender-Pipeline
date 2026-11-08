import bpy, os, re, getpass
from uuid import uuid4

from .transfer_map import TransferMap, TransferSettings
from .layers import listed_layers
from .utils import SourceFile, get_database, list_versions, latest_version, resolve_asset

class AssetBuilder:
	"""Constructs an asset by applying layers to the current scene."""
	def __init__(self, name: str):
		self.asset = name
		self.uuid = str(uuid4())

	def __get_versions(self, layer: str) -> dict[int, str]:
		"""Returns a list of all files for a layer"""

		# Structure is "master/wip/asset/layer/asset_layer_v001.blend" for now
		wip_folder = os.path.join(get_database(), "wip", self.asset, layer)
		if not os.path.exists(wip_folder):
			raise NotADirectoryError(f"Missing {layer} folder: {wip_folder}")

		return dict(list_versions(wip_folder))

	def __get_version(self, layer: str, version: int) -> SourceFile:
		"""Returns a layer file with a specific version"""

		versions = self.__get_versions(layer)
		if not versions:
			raise FileNotFoundError(f"No versions for {layer} exist!")

		if version not in versions:
			raise IndexError(f"Version {version} doesn't exist! Available: {sorted(versions)}")

		# SourceFile expects a version number starting at 1
		return SourceFile(versions[version], self.asset, layer, version)

	def __get_latest(self, layer: str) -> SourceFile:
		"""Returns the latest layer file available"""

		versions = self.__get_versions(layer)
		if not versions:
			raise FileNotFoundError(f"No versions for {layer} exist!")

		latest = max(versions)
		return SourceFile(versions[latest], self.asset, layer, latest)

	def mark_asset(self) -> None:
		"""Adds asset metadata and creates a root collection if needed"""

		root = None
		base = bpy.context.scene.collection
		if len(base.objects) == 0 and len(base.children) == 1:
			# If there's already a root collection, don't add another
			root = base.children[0]
			root.name = self.asset
		else:
			root = bpy.data.collections.new(self.asset)
			# Move children to new root collection. Copy to lists since stuff gets removed
			for col in list(base.children):
				root.children.link(col)
				base.children.unlink(col)
			for obj in list(base.objects):
				root.objects.link(obj)
				base.objects.unlink(obj)
			# Add root collection to scene
			base.children.link(root)

		root.asset_mark()
		try:
			root.asset_generate_preview()
		except Exception as err:
			# Previews can't always be generated, eg. in background mode
			print(f"WARNING: Couldn't generate asset preview: {err}")

		asset_data = root.asset_data
		asset_data.catalog_id = self.uuid
		asset_data.author = getpass.getuser()

	def process(self, layer, settings: TransferSettings, version: int=-1) -> None:
		"""
		Applies a layer with a specific version.\n
		Zero or negative uses the latest version.
		"""
		path = self.__get_version(layer.folder, version) if version > 0 else self.__get_latest(layer.folder)
		with TransferMap(path, layer.find_parents) as map:
			layer.process(map, settings)

	def __update_catalog(self, version: int) -> None:
		"""Manually updates Blender's Asset Library catalog file"""

		catalog_path = os.path.join(get_database(), "build", "blender_assets.cats.txt")
		catalog_exists = os.path.isfile(catalog_path)

		with open(catalog_path, "a", encoding="utf-8") as catalog:
			if not catalog_exists:
				# Write default content, requires folders have UUIDs for some reason
				catalog.write(f"VERSION 1\n\n{uuid4()}:Builds:Builds")
			# Catalog paths can't contain these characters
			name = re.sub(r"[:/\\]", "_", self.asset)
			name = name[:1].upper() + name[1:]
			# Structure is "Builds/Asset/Asset v001" for now
			catalog.write(f"\n{self.uuid}:Builds/{name}:{name} v{version:03d}")

	def save(self, write_catalog: bool=False) -> None:
		"""
		Saves the current Blender file in the builds folder.\n
		`write_catalog` optionally lists this file in the Asset Library.
		"""
		# Structure is "master/build/asset/asset_v001.blend" for now
		asset_folder = os.path.join(get_database(), "build", self.asset)
		os.makedirs(asset_folder, exist_ok=True)

		# Increase version based on the highest version in the subfolder
		version = latest_version(asset_folder) + 1

		# Name is "asset_v001.blend" for now
		file_name = f"{self.asset}_v{version:03d}.blend"
		file_path = os.path.join(asset_folder, file_name)

		bpy.ops.wm.save_mainfile(filepath=file_path)

		# Only list the build once it exists on disk
		if write_catalog:
			self.__update_catalog(version)
		print(f"Successfully built {file_path}")

def run_build(asset: str) -> None:
	"""Builds an asset from all of its layers and saves it"""
	if not get_database():
		raise RuntimeError("No database folder set! Use --database or the SG_DATABASE environment variable.")

	settings = TransferSettings()
	settings.update_transform = True
	# Avoid rebuilding material data in other layers
	settings.replacing_materials = True

	builder = AssetBuilder(resolve_asset(asset))
	for layer in listed_layers:
		try:
			builder.process(layer, settings, -1)
		except Exception as err:
			print(err)

	builder.mark_asset()
	builder.save(write_catalog=True)