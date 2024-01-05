# SPDX-FileCopyrightText: Stefan Tatschner
#
# SPDX-License-Identifier: CC0-1.0

{
  inputs = {
    nixpkgs.url = "nixpkgs";
  };

  outputs = { self, nixpkgs }:
    with import nixpkgs { system = "x86_64-linux"; };
    let pkgs = nixpkgs.legacyPackages.x86_64-linux;
    in {
      devShell.x86_64-linux = pkgs.mkShell {
        buildInputs = with pkgs; [ 
          go
          gnumake
          gopls
          gotools
        ];
      };
      formatter.x86_64-linux = pkgs.nixpkgs-fmt;
    };
}
