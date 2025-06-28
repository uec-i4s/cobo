{
  description = "TODO";

  inputs = {
    nixpkgs.url = "github:nixos/nixpkgs?ref=nixpkgs-unstable";
    pyproject-nix = {
      url = "github:pyproject-nix/pyproject.nix";
      inputs.nixpkgs.follows = "nixpkgs";
    };
    uv2nix = {
      url = "github:pyproject-nix/uv2nix";
      inputs.pyproject-nix.follows = "pyproject-nix";
      inputs.nixpkgs.follows = "nixpkgs";
    };
    pyproject-build-systems = {
      url = "github:pyproject-nix/build-system-pkgs";
      inputs.pyproject-nix.follows = "pyproject-nix";
      inputs.uv2nix.follows = "uv2nix";
      inputs.nixpkgs.follows = "nixpkgs";
    };
    flake-utils.url = "github:numtide/flake-utils";
    treefmt-nix = {
      url = "github:numtide/treefmt-nix";
      inputs.nixpkgs.follows = "nixpkgs";
    };
  };

  outputs =
    {
      self,
      nixpkgs,
      uv2nix,
      pyproject-nix,
      pyproject-build-systems,
      flake-utils,
      treefmt-nix,
    }:
    flake-utils.lib.eachDefaultSystem (
      system:
      let
        inherit (nixpkgs) lib;
        pkgs = nixpkgs.legacyPackages.${system};

        python = pkgs.python312; # .python-version
        venv =
          let
            workspace = uv2nix.lib.workspace.loadWorkspace { workspaceRoot = ./.; };
            overlay = workspace.mkPyprojectOverlay {
              sourcePreference = "wheel"; # or sourcePreference = "sdist";
            };
            pyprojectOverrides = final: prev: {
              onnxruntime = python.pkgs.onnxruntime;
              pypika = python.pkgs.pypika;
            };
            pythonSet =
              (pkgs.callPackage pyproject-nix.build.packages {
                inherit python;
              }).overrideScope
                (
                  lib.composeManyExtensions [
                    pyproject-build-systems.overlays.default
                    overlay
                    pyprojectOverrides
                  ]
                );
          in
          pythonSet.mkVirtualEnv "rag-mpc-venv" workspace.deps.default;
      in
      {
        packages.default = venv;

        devShells.default = pkgs.mkShellNoCC {
          packages =
            [
              python
              venv
            ]
            ++ (with pkgs; [
              nil
              pyright
              uv
            ]);
          env = {
            UV_PYTHON_DOWNLOADS = "never"; # Prevent uv from managing Python downloads
            UV_PYTHON = python.interpreter; # Force uv to use nixpkgs Python interpreter
          };
        };

        formatter = treefmt-nix.lib.mkWrapper pkgs {
          projectRootFile = "flake.nix";
          programs = {
            black.enable = true;
            nixfmt.enable = true;
          };
          settings.global.excludes = [
          ];
        };
      }
    );
}
