{pkgs}: {
  deps = [
    pkgs.redis
    pkgs.glibcLocales
    pkgs.postgresql
    pkgs.openssl
  ];
}
