<img src="./images/shitgrid.svg" width="75" align="left">

# Untitled Blender Pipeline

This pipeline was an experiment to see how much I could get done in 2 weeks.

I designed a versioning system around Blender's data blocks system. Each data block is associated with a version and layer.

Later I realised I was reinventing the wheel after looking at Kitsu's codebase, which uses the same idea of transferring data between objects.

<img src="./images/thumb.jpg" width="600">

| [Demo Video](https://youtu.be/tNqqY4XsTL0) |
| --- |

## Features

<img src="./images/features.png" width="600">

### Publishing

When publishing an asset, it works like a namespace. All data blocks relevant to the chosen publish layer get tagged with custom data.

Custom data is used to create an imaginary link, associating data blocks to an asset name, ID, layer and version.

Conceptually this means any data can be published, even if it can't be represented as an object (such as text, brushes, palettes, etc)

<img src="./images/assets.png" width="600">

Any data blocks which are already tagged won't get retagged. This is because a single Blender can contain multiple assets (for example when scene building), and publishing should only affect the relevant asset name.

If a data block is already tagged and belongs to the publish name and layer, its version in the custom data will be incremented.

### Updating

When updating, it searches through all data blocks and checks the version in their custom data. Any outdated data blocks will be rebuilt according to their layer.

<img src="./images/updating.png" width="600">

<img src="./images/updated.png" width="600">

### Fetching

Fetching is meant to append a prebuilt asset created by `build.bat`.

For the public release it checks whether builds exist, and otherwise manually builds all layers for an asset.

### Building

Building is a developer feature intended to manually build specific layers with specific versions. It turned out to be the most useful feature in practice.

<img src="./images/layers.png" width="600">

<img src="./images/layers2.png" width="600">

<img src="./images/built.png" width="600">

The Status on the Assets and Builds pages is based on the folders:

- **In progress** means something was published.
- **Built** means a layer is built.
- **Needs rebuild** means a layer was published after the latest build.

## Components

### Website

The website is designed to imitate Shotgrid, with basic abilities to create and view tasks and assets.

<img src="./images/dashboard.png" width="600">

When an asset is added via the frontend, the backend creates a folder on disk within the `wip` folder.

The Builds page reads the same folders the Blender addon writes to. It lists each asset's latest build and the latest published version of every layer (see [shared database](#shared-database)).

<img src="./images/wipfolder.png" width="600">

The folders are used by the Blender addon as described below.

### Blender Addon

The Blender addon is responsible for publishing, version control and building.

Once a `wip` asset folder is added via the website, the addon can publish Blender files into that folder. The asset name boxes in Publish and Fetch suggest every asset found in `wip` and `build`, so assets created on the website show up in Blender.

The build scripts take `wip` files and consolidate them into single assets, located in the `build` folder.

## Architecture

### Website Backend

The backend is written in JavaScript using Express.

It doesn't use a database for now, just basic file storage in `assets.json` and `tasks.json`.

| Endpoint | Description |
| --- | --- |
| `GET /assets/get`, `POST /assets/add` | List and add assets. Adding creates `wip/<asset>/` before saving `assets.json`. |
| `GET /tasks/get`, `POST /tasks/add` | List and add tasks |
| `GET /builds/get` | Status, versions in `build/<asset>/`, and the latest version of each layer in `wip/<asset>/<layer>/` |

By default the server only listens on `127.0.0.1` and only accepts localhost origins (see `SG_HOST` and `SG_CORS_ORIGIN` below).

<img src="images/web_backend_full.svg">

### Website Frontend

The frontend is written in JavaScript and JSX using React.

### Blender Addon

The Blender addon is written in Python.

## Shared Database

The website and the Blender addon share one folder, set with the `SG_DATABASE` environment variable:

```
SG_DATABASE/
  wip/<asset>/<layer>/<asset>_<layer>_v001.blend // Written by Publish in Blender
  build/<asset>/<asset>_v001.blend               // Written by build.bat and build_cli.py
```

## Environment Variables

For the website client and server, there's example files called `.env.example`. Copy them to `.env` to edit them.

### Shared

Keep these the same everywhere.

| Variable | Used by | Required | Description |
| --- | --- | --- | --- |
| `REACT_APP_SG_PORT` | Client and Server | Yes | Backend port, for example `5000`. |
| `SG_DATABASE` | Server and Blender Addon | Yes | The shared Blender database folder, for example `C:/blender_db`. |

### Client

| Variable | Required | Description |
| --- | --- | --- |
| `REACT_APP_SG_SERVER` | Yes | Backend URL including the scheme, for example `http://localhost`. |

### Server

| Variable | Required | Description |
| --- | --- | --- |
| `SG_WEB_DB` | Yes | Folder for the JSON files, for example `C:/web_db`. |
| `SG_HOST` | No | Host to listen on, for example `127.0.0.1`. |
| `SG_CORS_ORIGIN` | No | Comma-separated browser origins to allow. Defaults to any localhost origin. |

### Blender Addon

| Variable | Required | Description |
| --- | --- | --- |
| `BLENDER_EXE` | No | Path to `blender.exe`, used by `build.bat`. |

## Installation

### Website Frontend

1. Install NPM and Node.js
2. Go to `website/client`
3. Run `npm install`
4. Create `.env` from `.env.example`
5. Run `npm start`

### Website Backend

1. Install NPM and Node.js
2. Go to `website/server`
3. Run `npm install`
4. Create `.env` from `.env.example`
5. Run `npm run dev`. For older node versions, set the variables in your shell and run `npm start`.

### Blender Addon

1. Zip the `blender` folder
2. Open Blender preferences
3. Install the zipped folder as an addon
4. Press `N` to open the menu. The panels should be listed in the 3D Viewport sidebar.
