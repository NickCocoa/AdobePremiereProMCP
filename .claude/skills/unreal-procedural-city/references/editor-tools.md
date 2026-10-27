# Editor Utility Widget, presets and gameplay tags

One **Editor Utility Widget** drives all the tools. Keep buttons few and obvious.

## Buttons

| Button | What it does |
|---|---|
| **Generate Selected** | Runs the block processor or building graph on the selection (see `block-processor.md`) |
| **Bake Selected** | Dynamic mesh → static mesh asset, swaps the actor, keeps the spline (`scripts/unreal/bake_dynamic_meshes.py`) |
| **Refresh Selected** | `pcg.FlushCache` through *Execute Console Command*, then regenerate, without losing the preset on the actor (`scripts/unreal/regenerate_selected.py`) |
| **Random Building Tags** | Gives each selected building a random preset tag and regenerates; change a whole street's look in one click |
| **Create Preset** | Saves the selected building's settings as a preset (flow below) |
| **Bake Tile** (per tile) | World tiles manager bake (`roads-and-markings.md`) |

Every destructive action shows a **message dialog** first ("Overwrite existing preset?"). It saves work more often than you expect.

## Presets keyed by gameplay tags

- A **data table** of building presets; each row holds the full building setup (kits, floor styles, colours, roof, socket densities, interior layout).
- Each row is identified by a **gameplay tag** such as `Lucid.Buildings.NeoRenaissance.Corner`; use your own root, for example `City.Buildings.*`.
- Tags make it easy to organise styles and assign them in bulk, for example giving every OSM footprint a style from its building type.

### Create Preset flow

1. Is a building selected? If not, tell the user and stop.
2. Is the entered tag already in use?
   - No: add a data table row with the building's data.
   - Yes: ask "Overwrite this preset?" and only overwrite on Yes.
3. Save the data table and the tag config.

### Showing only the tool's tags

By default the tag picker lists every tag in the project. Filter it to the tool's own tags.

1. Add `"GameplayTags"` to `PublicDependencyModuleNames` in the plugin's `Build.cs`.
2. In the plugin module's `StartupModule()`, register the plugin's own tag folder so the tags it writes are loaded:

   ```cpp
   #include "GameplayTagsManager.h"
   #include "Interfaces/IPluginManager.h"

   void FCityToolsModule::StartupModule()
   {
       const TSharedPtr<IPlugin> Plugin = IPluginManager::Get().FindPlugin(TEXT("CityTools"));
       if (Plugin.IsValid())
       {
           UGameplayTagsManager::Get().AddTagIniSearchPath(Plugin->GetBaseDir() / TEXT("Config/Tags"));
       }
   }
   ```

3. The widget writes new tags to `Config/Tags/BuildingPresets.ini` inside the plugin, in the usual `[/Script/GameplayTags.GameplayTagsList]` with `GameplayTagList=(Tag="City.Buildings.…")` lines.
4. On the building class, filter the property to the tool's root:

   ```cpp
   UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Building", meta = (Categories = "City.Buildings"))
   FGameplayTag PresetTag;
   ```

## Making tools people use

- Keep the whole workflow inside Unreal, with as few steps as possible.
- Show work in progress to the environment artists and level designers who will use it, and change it from what they say.
- One plugin holds the tools; projects get versions of it instead of their own copies.
