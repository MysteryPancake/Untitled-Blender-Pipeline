import bpy, os
from typing import Any
from bpy.app.handlers import persistent
from uuid import uuid4

from .build import AssetBuilder
from .layers import listed_layers, layer_lookup, layer_menu, LayerMaterials
from .transfer_map import TransferSettings
from .utils import (
	ENV_VAR, get_prefs, get_database, get_blocks, list_versions, latest_version,
	clean_asset_name, resolve_asset, search_assets,
)

SG_KEYS = ("sg_asset", "sg_layer", "sg_version", "sg_id")
DATABASE_ERROR = "Set the SG_DATABASE environment variable and restart Blender"

bl_info = {
	"name": "Shitgrid Pipeline",
	"description": "Official Unofficial ALA Pipeline (Sponsored by Ian Hubert)",
	"author": "Animal Logic Academy",
	"version": (1, 0),
	"blender": (3, 4, 1),
	"location": "View 3D > Tool Shelf > Shitgrid",
	"support": "COMMUNITY",
	"category": "ALA",
}

def setup_asset_library() -> None:
	"""Registers the build folder to display in the asset library"""
	database = get_database()
	if not database:
		return
	build_folder = os.path.join(database, "build")
	if not os.path.isdir(build_folder):
		return

	libraries = bpy.context.preferences.filepaths.asset_libraries
	lib_name = "Asset Builds"

	# Don't add the same library twice, but follow the database if it moved
	for lib in libraries:
		if lib.name == lib_name:
			if os.path.normpath(lib.path) != os.path.normpath(build_folder):
				lib.path = build_folder
			return

	try:
		libraries.new(name=lib_name, directory=build_folder)
	except (AttributeError, TypeError):
		# Older Blender versions only have the operator
		bpy.ops.preferences.asset_library_add(directory=build_folder)
		libraries[-1].name = lib_name

def tag_data(data, name: str, layer: str, version: int) -> None:
	"""
	Tags a data block with custom data.\n
	This is used to associate everything with an asset, layer and version.\n
	`sg_id` is used for matching. Try to avoid duplicate IDs.\n
	When IDs are duplicated, it links by order.
	"""
	old_name = data.get("sg_asset")
	old_layer = data.get("sg_layer")
	if not old_name:
		# New data, set all properties
		data["sg_asset"] = name
		data["sg_layer"] = layer
		data["sg_version"] = version
		data["sg_id"] = str(uuid4())
	elif old_name == name and old_layer == layer:
		# Updated data, change version
		data["sg_version"] = version

class Preferences(bpy.types.AddonPreferences):
	"""Preferences for this addon"""
	bl_idname = __package__
	# Whether to check for updates on file load
	auto_update: bpy.props.BoolProperty(name="Auto Update", default=False)
	# Whether to automatically make an asset folder
	make_folder: bpy.props.BoolProperty(name="Make asset folder if missing", default=True)
	# Whether to show developer options on UI
	dev_mode: bpy.props.BoolProperty(name="Developer Mode", default=False)

	def draw(self, context):
		layout = self.layout
		database = get_database()
		if database:
			layout.label(text=f"Database Folder: {database}", icon="INFO")
		else:
			layout.label(text=f"The {ENV_VAR} environment variable isn't set", icon="ERROR")
		layout.prop(self, "dev_mode")
		layout.prop(self, "make_folder")

class Update_Item(bpy.types.PropertyGroup):
	"""Properties for items displayed in the update list"""
	# Name property is built-in
	asset: bpy.props.StringProperty(name="Asset Name")
	layers: bpy.props.CollectionProperty(type=bpy.types.PropertyGroup)
	outdated: bpy.props.BoolProperty(default=False)
	checked: bpy.props.BoolProperty(default=True)

class Properties(bpy.types.PropertyGroup):
	"""Properties shown in the UI panel"""
	# Publish properties
	publish_layer: bpy.props.EnumProperty(name="Layer", items=layer_menu)
	
	# Suggests assets from the shared database
	publish_asset: bpy.props.StringProperty(name="Asset Name", search=search_assets, search_options={"SORT", "SUGGESTION"})

	# Fetch properties
	fetch_asset: bpy.props.StringProperty(name="Asset Name", search=search_assets, search_options={"SORT", "SUGGESTION"})

	# Update properties
	show_update_list: bpy.props.BoolProperty(default=False)
	update_items: bpy.props.CollectionProperty(type=Update_Item)
	update_transform: bpy.props.BoolProperty(name="Update Transform", default=True)

	# Developer properties
	dev_build_layer: bpy.props.EnumProperty(name="Layer", items=layer_menu)
	dev_build_version: bpy.props.IntProperty(name="Version", default=1)

def get_transfer_settings(props: Properties):
	"""Builds transfer settings from UI panel properties"""
	settings = TransferSettings()
	settings.update_transform = props.update_transform
	return settings

def collect_image_nodes(node_tree, found: list[Any], seen: set[int]) -> None:
	"""Collects images used in a node tree, including nested node groups"""
	if node_tree is None or node_tree.as_pointer() in seen:
		return
	seen.add(node_tree.as_pointer())
	for node in node_tree.nodes:
		if node.type == "TEX_IMAGE" and node.image:
			found.append(node.image)
		elif node.type == "GROUP":
			collect_image_nodes(node.node_tree, found, seen)

def collect_publish_blocks(scene: bpy.types.Scene, layer) -> list[Any]:
	"""
	Finds the data blocks of a layer which belong to this scene's asset.\n
	Orphans and data from other scenes or assets aren't tagged.
	"""
	root = scene.collection
	objects = list(root.all_objects)
	blocks: list[Any] = list(root.children_recursive) + objects

	# Sub object data blocks that belong to this layer
	wanted: set[int] = set()
	for data_type in layer.trigger_update:
		wanted.update(block.as_pointer() for block in get_blocks(data_type))

	candidates: list[Any] = [scene.world]
	for obj in objects:
		data = obj.data
		candidates.append(data)
		candidates.append(getattr(data, "shape_keys", None))
		for slot in obj.material_slots:
			candidates.append(slot.material)
		for system in getattr(obj, "particle_systems", ()):
			candidates.append(system.settings)

	# Textures used by materials and worlds
	images: list[Any] = []
	seen: set[int] = set()
	for candidate in candidates:
		node_tree = getattr(candidate, "node_tree", None)
		if node_tree:
			collect_image_nodes(node_tree, images, seen)
	candidates.extend(images)

	added: set[int] = set()
	for candidate in candidates:
		if candidate is None:
			continue
		pointer = candidate.as_pointer()
		if pointer in wanted and pointer not in added:
			added.add(pointer)
			blocks.append(candidate)
	return blocks

class Publish_Operator(bpy.types.Operator):
	"""Save and increment the version of the above assets"""
	bl_idname = "pipeline.publish"
	bl_label = "Publish Asset"

	def execute(self, context):
		props = context.scene.sg_props
		if not props.publish_layer:
			self.report({"ERROR_INVALID_INPUT"}, "Please select a layer!")
			return {"CANCELLED"}
		try:
			asset = clean_asset_name(props.publish_asset)
		except ValueError as err:
			self.report({"ERROR_INVALID_INPUT"}, str(err))
			return {"CANCELLED"}

		database = get_database()
		if not database:
			self.report({"ERROR"}, DATABASE_ERROR)
			return {"CANCELLED"}
		# Reuse the existing spelling so "rock" doesn't become a second asset next to "Rock"
		asset = resolve_asset(asset)
		wip_folder = os.path.join(database, "wip", asset)
		if not os.path.exists(wip_folder):
			if get_prefs(context).make_folder:
				os.makedirs(wip_folder, exist_ok=True)
			else:
				self.report({"ERROR"}, f"Asset folder '{asset}' doesn't exist yet!")
				return {"CANCELLED"}

		# Structure is "master/wip/asset/layer/asset_layer_v001.blend" for now
		layer_folder = os.path.join(wip_folder, props.publish_layer)
		os.makedirs(layer_folder, exist_ok=True)

		# Up version number based on the highest version found in the subfolder
		version = latest_version(layer_folder) + 1

		# Name is "asset_layer_v001.blend" for now
		file_name = f"{asset}_{props.publish_layer}_v{version:03d}.blend"
		path = os.path.join(layer_folder, file_name)

		# I'm using custom data to associate data blocks with an asset, version and layer
		# Tag all collections, objects and layer data which haven't already been tagged
		# Sub object data blocks are included when they belong to this layer
		blocks = collect_publish_blocks(context.scene, layer_lookup[props.publish_layer])

		# Remember the previous tags so they can be restored if saving fails
		snapshot = [(block, {k: block[k] for k in SG_KEYS if k in block}) for block in blocks]

		for block in blocks:
			tag_data(block, asset, props.publish_layer, version)

		# Save a copy in the "wip" folder, this copy should never be touched!
		try:
			bpy.ops.wm.save_as_mainfile(filepath=path, check_existing=True, copy=True)
		except Exception as err:
			# Revert tags, since the version doesn't exist on disk
			for block, old in snapshot:
				for key in SG_KEYS:
					if key in old:
						block[key] = old[key]
					else:
						block.pop(key, None)
			self.report({"ERROR"}, f"Failed to save publish: {err}")
			return {"CANCELLED"}

		# Would be nice to add a popup for this
		success_msg = f"Published {asset} {props.publish_layer} version {version}!"
		self.report({"INFO"}, success_msg)

		return {"FINISHED"}

class Publish_Panel(bpy.types.Panel):
	bl_label = "Publish"
	bl_idname = "ALA_PT_Publish"
	bl_space_type = "VIEW_3D"
	bl_region_type = "UI"
	bl_category = "Shitgrid"

	def draw(self, context):
		props = context.scene.sg_props
		layout = self.layout
		layout.prop(props, "publish_asset")
		layout.prop(props, "publish_layer")
		layout.operator(Publish_Operator.bl_idname, icon="EXPORT")

def get_updates() -> dict[str, list[Any]]:
	"""Builds a list of layer updates per asset"""
	database = get_database()

	# Using a list instead of a set to preserve layer order
	updates: dict[str, list[Any]] = {}
	if not database:
		return updates

	# Find outdated data blocks
	for layer in listed_layers:
		for data_type in layer.trigger_update:
			for block in get_blocks(data_type):
				asset = block.get("sg_asset")
				if not asset:
					continue

				if asset not in updates:
					updates[asset] = []

				block_layer = block.get("sg_layer")
				current = block.get("sg_version")
				if not block_layer or current is None:
					continue

				# Don't check outdated layers again
				if block_layer in updates[asset]:
					continue

				folder = os.path.join(database, "wip", asset, block_layer)
				if not os.path.exists(folder):
					continue

				if latest_version(folder) > current:
					updates[asset].append(block_layer)
	return updates

class Check_Updates_Operator(bpy.types.Operator):
	"""Check if asset updates are available"""
	bl_idname = "pipeline.check_updates"
	bl_label = "Check for Updates"

	def execute(self, context):
		# Clear previously listed updates
		props = context.scene.sg_props
		props.update_items.clear()

		# Build update list UI
		updates = get_updates()
		for asset in updates:
			layer_order = updates[asset]
			layers = ", ".join(layer_order) if layer_order else "Up to date"

			# Add UI list entry
			item = props.update_items.add()
			item.name = f"{asset} ({layers})"
			item.asset = asset
			for layer_name in layer_order:
				layer = item.layers.add()
				layer.name = layer_name
			item.outdated = bool(layer_order)
		
		props.show_update_list = True

		return {"FINISHED"}

class Update_Operator(bpy.types.Operator):
	"""Apply selected updates to assets"""
	bl_idname = "pipeline.update"
	bl_label = "Apply Updates"
	bl_options = {"REGISTER", "UNDO"}

	def execute(self, context):
		props = context.scene.sg_props
		if not get_database():
			self.report({"ERROR"}, DATABASE_ERROR)
			return {"CANCELLED"}
		settings = get_transfer_settings(props)
		try:
			for item in props.update_items:
				# Skip unchecked items
				if not item.checked or not item.outdated:
					continue
				# Avoid rebuilding material data in other layers
				replacing_mats = LayerMaterials.folder in [layer.name for layer in item.layers]
				settings.replacing_materials = replacing_mats

				# This assumes correct layer ordering from Check_Updates
				builder = AssetBuilder(item.asset)
				for layer in item.layers:
					layer_obj = layer_lookup[layer.name]
					try:
						builder.process(layer_obj, settings, -1)
					except Exception as err:
						self.report({"WARNING"}, str(err))

				item.name = f"{item.asset} (Up to date)"
				item.layers.clear()
				item.outdated = False

			return {"FINISHED"}
		
		except Exception as err:
			self.report({"ERROR"}, str(err))
			return {"CANCELLED"}

class Update_Close_Operator(bpy.types.Operator):
	"""Close updates list"""
	bl_idname = "pipeline.close_update"
	bl_label = "Close"

	def execute(self, context):
		props = context.scene.sg_props
		props.show_update_list = False
		return {"FINISHED"}

class Update_Panel(bpy.types.Panel):
	bl_label = "Update"
	bl_idname = "ALA_PT_Update"
	bl_space_type = "VIEW_3D"
	bl_region_type = "UI"
	bl_category = "Shitgrid"

	def draw(self, context):
		layout = self.layout
		props = context.scene.sg_props

		# Auto-update button
		layout.prop(get_prefs(context), "auto_update")

		# Check updates and close button
		if props.show_update_list:
			layout.operator(Update_Close_Operator.bl_idname, icon="PANEL_CLOSE")
		else:
			layout.operator(Check_Updates_Operator.bl_idname, icon="FILE_REFRESH")
		
		if not props.show_update_list:
			return

		update_list = layout.box().column()
		if props.update_items:
			
			outdated = False
			update_list.label(text="Update Status:")
			for item in props.update_items:
				outdated = outdated or item.outdated
				row = update_list.row()
				row.enabled = item.outdated
				row.prop(
					item,
					"checked",
					icon="CHECKBOX_HLT" if item.checked or not item.outdated else "CHECKBOX_DEHLT",
					text="",
					emboss=False
				)
				row.label(text=item.name)

			if outdated:
				# Update button
				layout.operator(Update_Operator.bl_idname, icon="SORT_ASC")
				# Update transform checkbox
				layout.prop(props, "update_transform")
		else:
			update_list.label(text="No assets found!")

class Fetch_Operator(bpy.types.Operator):
	"""Fetch the latest approved asset build"""
	bl_idname = "pipeline.fetch"
	bl_label = "Fetch Asset"
	bl_options = {"REGISTER", "UNDO"}

	def execute(self, context):
		props = context.scene.sg_props
		if not props.fetch_asset:
			self.report({"ERROR_INVALID_INPUT"}, "Please type in an asset!")
			return {"CANCELLED"}

		asset = resolve_asset(props.fetch_asset)

		# Check for prebuilds generated by build.bat
		database = get_database()
		if not database:
			self.report({"ERROR"}, DATABASE_ERROR)
			return {"CANCELLED"}
		build_folder = os.path.join(database, "build", asset)
		if not os.path.exists(build_folder):
			self.report({"WARNING"}, f"Build folder for '{asset}' doesn't exist yet!")

			# Build asset live when prebuilds aren't available
			settings = get_transfer_settings(props)
			# Avoid rebuilding material data in other layers
			settings.replacing_materials = True

			builder = AssetBuilder(asset)
			for layer in listed_layers:
				try:
					builder.process(layer, settings, -1)
				except Exception as err:
					self.report({"WARNING"}, str(err))
		else:
			# Sorted by version number
			versions = [path for _, path in list_versions(build_folder)]
			if not versions:
				self.report({"ERROR"}, f"Builds for '{asset}' don't exist yet!")
				return {"CANCELLED"}

			# Assume top collection is the root we need to import
			latest_path = versions[-1]
			has_collections = True
			with bpy.data.libraries.load(latest_path, link=False) as (source_data, target_data):
				if source_data.collections:
					target_data.collections = [source_data.collections[0]]
				else:
					has_collections = False

			if not has_collections:
				self.report({"ERROR"}, "Build contains no collections!")
				return {"CANCELLED"}

			# Add to our Scene Collection
			for col in target_data.collections:
				context.scene.collection.children.link(col)

		return {"FINISHED"}

class Fetch_Panel(bpy.types.Panel):
	bl_label = "Fetch"
	bl_idname = "ALA_PT_Fetch"
	bl_space_type = "VIEW_3D"
	bl_region_type = "UI"
	bl_category = "Shitgrid"

	def draw(self, context):
		props = context.scene.sg_props
		layout = self.layout
		layout.prop(props, "fetch_asset")
		layout.operator(Fetch_Operator.bl_idname, icon="IMPORT")

class Dev_Build_Operator(bpy.types.Operator):
	"""Build the asset layer by adding, removing and updating data"""
	bl_idname = "pipeline.build_layer"
	bl_label = "Build Asset Layer"
	bl_options = {"REGISTER", "UNDO"}
	
	def execute(self, context):
		props = context.scene.sg_props
		if not props.fetch_asset:
			self.report({"ERROR_INVALID_INPUT"}, "Please type in an asset!")
			return {"CANCELLED"}
		if not get_database():
			self.report({"ERROR"}, DATABASE_ERROR)
			return {"CANCELLED"}
		builder = AssetBuilder(resolve_asset(props.fetch_asset))
		settings = get_transfer_settings(props)
		layer = layer_lookup[props.dev_build_layer]
		try:
			builder.process(layer, settings, props.dev_build_version)
			return {"FINISHED"}
		except Exception as err:
			self.report({"ERROR"}, str(err))
			return {"CANCELLED"}

class Build_Panel(bpy.types.Panel):
	bl_label = "(DEV) Build"
	bl_idname = "ALA_PT_Build"
	bl_space_type = "VIEW_3D"
	bl_region_type = "UI"
	bl_category = "Shitgrid"

	def draw(self, context):
		props = context.scene.sg_props
		layout = self.layout

		layout.use_property_split = True
		layout.use_property_decorate = False
		
		layout.prop(props, "fetch_asset")
		layout.prop(props, "dev_build_layer")
		layout.prop(props, "dev_build_version")
		layout.prop(props, "update_transform")
		layout.operator(Dev_Build_Operator.bl_idname)

	@classmethod
	def poll(cls, context):
		return get_prefs(context).dev_mode

def get_selected_blocks(context: bpy.types.Context) -> set[Any]:
	"""Gets selected asset data blocks in the outliner"""
	blocks = set()
	# Include data blocks selected in scene
	for block in context.selected_objects:
		if block.get("sg_asset"):
			blocks.add(block)

	# Include data blocks selected in outliner
	for area in context.screen.areas:
		if area.type != "OUTLINER":
			continue
		with context.temp_override(window=context.window, area=area):
			for block in context.selected_ids:
				if block.get("sg_asset"):
					blocks.add(block)
	return blocks

class Clear_Data_Operator(bpy.types.Operator):
	"""Clears custom data used to tag asset data blocks"""
	bl_idname = "pipeline.clear_data"
	bl_label = "Unlink Asset"
	bl_options = {"REGISTER", "UNDO"}

	def execute(self, context):
		for block in get_selected_blocks(context):
			for key in SG_KEYS:
				block.pop(key, None)
		return {"FINISHED"}

class Inspect_Panel(bpy.types.Panel):
	bl_label = "Inspect"
	bl_idname = "ALA_PT_Inspect"
	bl_space_type = "VIEW_3D"
	bl_region_type = "UI"
	bl_category = "Shitgrid"

	def draw(self, context):
		layout = self.layout
		blocks = get_selected_blocks(context)
		if not blocks:
			layout.label(text="No assets selected")
			return
		
		# Yuck code here, no idea how to draw a table properly
		cols = layout.column_flow(columns=4)
		cols.label(text="Type")
		cols.label(text="Asset")
		cols.label(text="Layer")
		cols.label(text="Version")
		item_list = layout.box().column()
		for block in blocks:
			# Table columns
			cols = item_list.column_flow(columns=4)
			cols.label(text=type(block).__name__)
			cols.label(text=block.get("sg_asset", "None"))
			cols.label(text=block.get("sg_layer", "None"))
			cols.label(text=str(block.get("sg_version", "None")))
		# Clear asset data button
		layout.operator(Clear_Data_Operator.bl_idname, icon="UNLINKED")

@persistent
def load_handler(dummy):
	# Auto-update if required
	prefs = get_prefs()
	if prefs is None or not prefs.auto_update:
		return

	scene = bpy.context.scene
	if scene is None or not hasattr(scene, "sg_props"):
		return
	props = scene.sg_props
	settings = get_transfer_settings(props)
	updates = get_updates()
	for asset in updates:
		layers = updates[asset]
		# Avoid rebuilding material data in other layers
		replacing_mats = LayerMaterials.folder in layers
		settings.replacing_materials = replacing_mats

		builder = AssetBuilder(asset)
		for layer in layers:
			layer_obj = layer_lookup[layer]
			try:
				builder.process(layer_obj, settings, -1)
			except Exception as err:
				print(err)

# Dump all classes to register in here
classes = [
	Publish_Panel, Update_Panel, Fetch_Panel, Inspect_Panel, Build_Panel,
	Publish_Operator, Check_Updates_Operator, Update_Operator, Clear_Data_Operator,
	Update_Close_Operator, Fetch_Operator, Dev_Build_Operator, Update_Item,
	Properties, Preferences
]

def register() -> None:
	for cls in classes:
		bpy.utils.register_class(cls)

	scn = bpy.types.Scene
	scn.sg_props = bpy.props.PointerProperty(type=Properties)
	bpy.app.handlers.load_post.append(load_handler)
	# Preferences aren't ready during register, so run this once shortly after
	bpy.app.timers.register(setup_asset_library, first_interval=0.1)

def unregister() -> None:
	scn = bpy.types.Scene
	del scn.sg_props

	if bpy.app.timers.is_registered(setup_asset_library):
		bpy.app.timers.unregister(setup_asset_library)
	if load_handler in bpy.app.handlers.load_post:
		bpy.app.handlers.load_post.remove(load_handler)

	for cls in classes:
		bpy.utils.unregister_class(cls)

if __name__ == "__main__":
	register()