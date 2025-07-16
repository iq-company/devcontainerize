# Getting started

## Prerequisites

In order to start developing you need to satisfy the following prerequisites:

- Docker
- docker-compose
- user added to docker group

It is recommended you allocate at least 4GB of RAM to docker

## Use VSCode Remote Containers extension

For most people getting started with Frappe development, the best solution is to use [VSCode Dev Containers extension](https://marketplace.visualstudio.com/items?itemName=ms-vscode-remote.remote-containers).

VSCode should automatically inquire you to install the required extensions, that can also be installed manually as follows:

- Install Dev Containers for VSCode
  - through command line `code --install-extension ms-vscode-remote.remote-containers`
  - clicking on the Install button in the Vistual Studio Marketplace: [Dev Containers](https://marketplace.visualstudio.com/items?itemName=ms-vscode-remote.remote-containers)
  - View: Extensions command in VSCode (Windows: Ctrl+Shift+X; macOS: Cmd+Shift+X) then search for extension `ms-vscode-remote.remote-containers`

After the extensions are installed, you can:

- Open this repository folder in VS Code.
  - `code .`
- Launch the command, from Command Palette (Ctrl + Shift + P) `Dev Containers: Reopen in Container`. You can also click in the bottom left corner to access the remote container menu.

## Windows FS and performance

https://code.visualstudio.com/remote/advancedcontainers/improve-performance

## Remove all

To remove all containers, volumes, etc. Use `F1` -> `Run Task` -> `Remove Containers and Volume`
