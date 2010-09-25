-- TODO: Implement test mode for model creation which adds check-constraintegers
-- for foreign keys and data types

-- Music information
create table artist (
  id               integer primary key,
  mb_id            text,
  name             text
);

create table album (
  id               integer primary key,
  mb_id            text,
  name             text
);

create table song (
  id               integer primary key,
  name             text,
  mb_id            text
);

create table music_info (
  id               integer primary key,
  artist_id        integer
     references artist(id),
  album_id         integer
     references album(id),
  song_id          integer
     references song(id)
);


-- Files
create table folder (
  id               integer primary key,
  name             text,
  full_path        text,
  is_mount_point   boolean, 
  hash             text,
  hash_is_wrong    integer default 0, --bool
  parent_folder_id integer
     references folder(id),
  unique(full_path),
  unique(name, parent_folder_id)
);

create table file (
  id               integer primary key,
  folder_id        integer
    references folder(id),
  name             text,
  hash             text,
  hash_is_wrong    integer default 0, --bool
  filetype         text,
  encoding         text,
  bitrate          text
);

create table file_mapping (
  id               integer primary key,
  file_id          integer
    references file(id),
  song_id          integer
    references song(id),
  album_id         integer
    references album(id),
  artist_id        integer
     references artist(id)
-- only one of (song_id, album_id, artist_id) may be filled
);

-- Collections and tags
create table mucouser (
  id               integer primary key,
  name             text,
  import           text,
  remove           text,
  change_data      text
);

create table collection (
  id               integer primary key,
  name            text,
  user_id         integer
    references mucouser(id)
);

create table collection_mapping (
  id              integer primary key,
  collection_id   integer
    references collection(id),
  song_id         integer
    references song(id),
  album_id        integer
    references album(id),
  artist_id       integer
    references artist(id)
  -- only one of (song_id, album_id, artist_id) may be filled
);

create table tag (
  id              integer primary key,
  name            text,
  user_id         integer
);

create table tag_mapping (
  id              integer primary key,
  tag_id          integer
    references tag(id),
  song_id         integer
    references song(id),
  album_id        integer
    references album(id),
  artist_id       integer
    references artist(id)
  -- only one of (song_id, album_id, artist_id) may be filled
);

PRAGMA foreign_keys = 1;

