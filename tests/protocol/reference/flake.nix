{
  description = "Pinned MPD 0.19 reference for Mopidy-MPD protocol tests";

  inputs.workspace.url = "git+https://github.com/mopidy/workspace.git?rev=edde6834ee771f87407898513c5feba74f566256";
  inputs.mpd = {
    url = "git+https://github.com/MusicPlayerDaemon/MPD.git?rev=3bbcda917ce7cb2fa6dcc90d6c38333ca855c941";
    flake = false;
  };

  outputs =
    { workspace, mpd, ... }:
    let
      system = "x86_64-linux";
      pkgs = workspace.inputs.nixpkgs.legacyPackages.${system};
      workspaceShell = workspace.devShells.${system}.default;
      reference = pkgs.stdenv.mkDerivation {
        pname = "mpd-reference";
        version = "0.19.21";
        src = mpd;

        nativeBuildInputs = with pkgs; [
          autoconf
          automake
          libtool
          pkg-config
        ];
        buildInputs = with pkgs; [
          boost
          glib
          flac
          libsndfile
        ];

        preConfigure = "./autogen.sh";
        configureFlags = [
          "--disable-icu"
          "--enable-flac"
          "--enable-sndfile"
          "--with-zeroconf=no"
          "--disable-inotify"
          "--disable-documentation"
        ];
      };
      runner = pkgs.writeShellApplication {
        name = "mpd-protocol-reference";
        runtimeInputs = [ reference ] ++ workspaceShell.nativeBuildInputs ++ workspaceShell.buildInputs;
        text = ''
          export UV_PYTHON_DOWNLOADS=never
          export TOX_UV_PATH=${pkgs.uv}/bin/uv
          export PYRIGHT_PYTHON_GLOBAL_NODE=1
          ${workspaceShell.shellHook}
          export MPD_REFERENCE_BIN=${reference}/bin/mpd
          exec tox -e 3.13 -- tests/protocol/test_reference.py --no-cov "$@"
        '';
      };
    in
    {
      packages.${system}.default = reference;
      apps.${system}.default = {
        type = "app";
        program = "${runner}/bin/mpd-protocol-reference";
      };
    };
}
