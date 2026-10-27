"""Shared helpers for the editor scripts. Runs inside Unreal Editor's Python only."""
import unreal


def actor_subsystem():
    return unreal.get_editor_subsystem(unreal.EditorActorSubsystem)


def editor_world():
    return unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).get_editor_world()


def selected_actors():
    return list(actor_subsystem().get_selected_level_actors())


def components(actor, cls):
    return list(actor.get_components_by_class(cls))


def console(command):
    unreal.SystemLibrary.execute_console_command(editor_world(), command)


def flush_pcg_cache():
    console("pcg.FlushCache")


def generate_pcg(actor, force=True):
    """Regenerate every PCG component on the actor. Returns how many were triggered."""
    count = 0
    for comp in components(actor, unreal.PCGComponent):
        for name in ("generate_local", "generate"):
            fn = getattr(comp, name, None)
            if fn:
                fn(force)
                count += 1
                break
    return count


def call_if_present(actor, function_name, *args):
    """Call a Blueprint function on the actor if it exists; returns True when called."""
    try:
        actor.call_method(function_name, tuple(args))
        return True
    except Exception as e:  # missing function or wrong signature
        unreal.log_warning(f"{actor.get_actor_label()}: could not call {function_name}: {e}")
        return False


def log(msg):
    unreal.log(f"[city-tools] {msg}")
