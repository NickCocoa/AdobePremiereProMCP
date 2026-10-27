# Performance

## PCG profiler

Open the profiler for the graph and run it. It lists how long each node takes, so you see the expensive part instead of guessing. Typical culprits:

- **Intersections** and **loops** that process the same data many times.
- Data that rides through the whole graph but is only used once early on.

Fixes, usually small and adding up:

- Send less data into loops, or replace the loop with a node that works on the whole set.
- Delete nodes you don't need; strip attributes that later nodes don't read (**Delete Attributes**).
- Filter points as early as possible.

Test at scale: a graph that's fast on one test building can run hundreds of times across a city.

## Editor responsiveness

- Untick **Run Construction Script on Drag** on spline blueprints (Class Settings).
- Don't use the *Generated Dynamic Mesh Actor* class for heavy work; rebuild from a button.
- Bake dynamic meshes to static meshes; nothing generates at runtime.
- Remesh low before ray-casting or booleans; remesh up afterwards.

## Rendering

- Nanite on all opaque meshes; glass separate via sockets.
- Instanced static meshes for panels and street furniture (the Static Mesh Spawner does this).
- Parallax interiors for floors the player can't enter.
- Colour and wear through custom primitive data, so instances keep sharing one material.
