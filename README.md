<img src="./images/shitgrid.svg" width="75" align="left">

# Untitled Blender Pipeline

This pipeline was an experiment to see how much I could get done in 2 weeks.

It was made during my holiday break at ALA in 2023. The idea was to use it for our coursework in Blender next semester. Sadly they picked a different pipeline called [Shino](https://superhivemarket.com/products/shino) instead.

I designed a versioning system around [Blender's data blocks](https://docs.blender.org/manual/en/latest/files/data_blocks.html) system. Each data block gets tagged with a version and layer, like `modelling`, `surfacing` or `lighting`. The build script merges all the layers into a single asset.

You can create and check the status of assets on the frontend website. The backend creates `wip` and `build` folders for Blender to use.

Later I realised I reinvented the wheel after looking at [Kitsu's codebase](https://studio.blender.org/tools/addons/blender_kitsu). They used the same idea of transferring data between objects.

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

## Components

### Website

The website is designed to imitate Shotgrid, with basic abilities to create and view tasks and assets.

<img src="./images/dashboard.png" width="600">

When an asset is added via the frontend, the backend creates a folder on disk within the `wip` folder.

<img src="./images/wipfolder.png" width="600">

The folders are used by the Blender addon as described below.

### Blender Addon

The Blender addon is responsible for publishing, version control and building.

Once a `wip` asset folder is added via the website, the addon can publish Blender files into that folder.

The build scripts take `wip` files and consolidate them into single assets, located in the `build` folder.

## Architecture

### Website Backend

The backend is written in JavaScript using Express.

It doesn't use a database for now, just basic file storage in `assets.json` and `tasks.json`.

<img src="images/web_backend_full.svg">

### Website Frontend

The frontend is written in JavaScript and JSX using React.

### Blender Addon

The Blender addon is written in Python.

## Environment Variables

### Website

- Set `SG_WEB_DB` to the folder you want the JSON files to be stored, for example `C:/web_db`
- Set `REACT_APP_SG_SERVER` to whatever URL the backend is hosted on, for example `http://localhost`
- Set `REACT_APP_SG_PORT` to whatever port the backend is hosted on, for example `5000`

### Blender Addon

- The Blender database must be set in the addon preferences.
- Set it to the folder you want Blender files to be saved, for example `C:/blender_db`

## Installation

### Website Frontend

1. Install NPM and Node.js
2. Go to `website/client`
3. Run `npm install`
4. Run `npm start`

### Website Backend

1. Install NPM and Node.js
2. Go to `website/server`
3. Run `npm install`
4. Run `npm start`

### Blender Addon

1. Zip the `blender` folder
2. Open Blender preferences
3. Install the zipped folder as an addon
4. Press `N` to open the menu. The panels should be listed in the 3D Viewport sidebar.
