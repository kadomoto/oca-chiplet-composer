# Your first package

In this tutorial you build a three-chiplet package from an empty substrate, then read what the analytic models say about it. It takes about ten minutes and needs only the composer, not the virtual platform.

When you finish, you have an IO chiplet linked to two compute chiplets on a UCIe-S organic package, a traffic flow between them, a clean set of design rules, and a sweep that compares package technologies.

## Before you start

[Install](install.md) the composer and open <http://127.0.0.1:8765>.

## 1. Start from an empty package

The example design loads on first start. Select each chiplet and press <kbd>Delete</kbd>, or select them in the **Objects** list in the right-hand inspector, until the substrate is empty.

In the header, keep **UCIe-S (standard organic, 2D)** and set the substrate to `30` × `24` mm.

## 2. Place three chiplets

From the left palette, drag an **IO / Host chiplet** onto the substrate, then two **Compute chiplets**. Each is drawn to scale.

Put the IO die on the left and the two compute dies to its right, one above the other. To place them exactly, select a die and type its **X** and **Y** in the inspector, or move it with the arrow keys (0.5 mm steps, 2 mm with <kbd>Shift</kbd>).

!!! tip
    The **Checks** tab updates as you move. If two dies come closer than the package's minimum gap (0.5 mm on organic), it reports which ones.

## 3. Link them

Press **Link tool** (or <kbd>L</kbd>), click the IO die, then the first compute die. Do the same for the second compute die. Press <kbd>Esc</kbd> to leave the tool.

Each link gets a UCIe PHY, drawn as a gold bump field, on the facing edge of both dies, and a route between them. Select a link to see its channel length, lanes, bandwidth and latency in the inspector.

## 4. Add traffic

Open the **Traffic** tab and press **Add flow**. Set the source to one compute die, the destination to the other, and the bandwidth to `20` GB/s.

There is no direct link between the two compute dies, so the flow goes through the IO die. The table shows the path, the zero-load latency, and the latency under load. The **Links** tab shows each link's utilisation.

## 5. Read the summary

The title block above the canvas sums up the design: design rules, die area, substrate fill, power, die-to-die power, the highest link utilisation, the worst flow latency, and silicon plus package cost.

Add a direct link between the two compute dies. The flow now takes it, its latency drops by one hop, and the IO links carry nothing.

## 6. Try another package

Switch the header to **UCIe-A (Si interposer, 2.5D)**. UCIe-A reaches only 2 mm, so the links between dies a few millimetres apart turn into design rule errors. Move the dies together until **Checks** is clean again. The canvas now draws a silicon interposer under them.

## 7. Compare with a sweep

Open the **Sweep** tab, choose **Package technology** and plot **Silicon + package cost**, then press **Run sweep**. Each point says whether the design passes its rules with that technology.

## Next

- [Simulate links on the Harness](../tutorials/two-die.md) runs this design on the virtual platform.
- [Packages and design rules](../guide/packages.md) explains each rule and default.
