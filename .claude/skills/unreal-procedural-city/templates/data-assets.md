# Data assets and structs

Create these as Blueprint structs and Primary Data Assets (or C++ `USTRUCT`/`UPrimaryDataAsset` in the plugin). Names are suggestions.

## `S_BuildingPanel`

| Field | Type | Notes |
|---|---|---|
| `Mesh` | Static Mesh (soft) | Nanite, pivot at bottom-left of the panel face |
| `Width` | float (cm) | Module size for the grammar |
| `Symbol` | Name | Grammar symbol, unique within a stack (`NR_W`, `NR_D`) |
| `IsRoomCorner` | bool | Emits an interior room point |
| `IsDoor` | bool | Emits a door point |
| `AdaptiveBase` | bool | Ground-floor panel whose base stretches to the ground |

## `DA_PanelKit` (data asset)

| Field | Type |
|---|---|
| `Panels` | array of `S_BuildingPanel` |
| `Trims` | array of meshes (horizontal, vertical, corner) |
| `GlassMesh` | Static Mesh, attached at `SOCKET_Glass` |

## `S_FloorStyle`

| Field | Type | Notes |
|---|---|---|
| `Height` | float (cm) | |
| `Positions` | set of enum `Ground, LowerTier, Middle, UpperTier, Top` | Where this style applies |
| `FrontGrammar` / `BackGrammar` / `LeftGrammar` / `RightGrammar` | string | e.g. `A,[B,B,C,B,B,A]*,D` |

## `S_SocketCategory`

| Field | Type |
|---|---|
| `SocketPrefix` | Name (`SOCKET_Balcony`) |
| `Meshes` | array of meshes or actor classes |
| `Density` | float 0–1 |
| `Enabled` | bool |

## `S_RoomSpace`

| Field | Type |
|---|---|
| `RoomId` | int |
| `RoomGraph` | PCG graph (soft) |
| `Space` | enum `World, Local` |

## `S_BuildingPreset` (data table row, keyed by gameplay tag)

| Field | Type |
|---|---|
| `Tag` | Gameplay Tag (`City.Buildings.*`) |
| `Kits` | array of `DA_PanelKit` (stacked) |
| `Floors` | array of `S_FloorStyle` |
| `WallColor`, `TrimColor`, `WindowColor` | Linear Color |
| `RoofStyle` | enum or data asset |
| `Sockets` | array of `S_SocketCategory` |
| `Rooms` | array of `S_RoomSpace` |
| `CornerRadius` | float (0 = sharp) |

## `DA_Neighbourhood`

Overrides `Sockets` densities and colour ranges for every building inside a zone volume: residential, industrial, commercial.
