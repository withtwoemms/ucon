# The Unity-Distance Metric

The **Unity-Distance Metric** provides a principled method for selecting the most natural scale prefix (e.g., kilo, mega, milli) for a given value.

It defines “nearness” not as linear numerical proximity, but as proximity in **order of magnitude** — that is, how close a value is to **unity (1)** when normalized by a candidate scale. This shift from linear to logarithmic thinking brings mathematical rigor to what users intuitively mean when they say a quantity _“belongs”_ to a certain scale.

---

## 1. Why Linear Distance Fails

Linear distance (`|x − s|`) feels intuitive because it mirrors ordinary subtraction. However, it collapses at extremes: the gap between 10³ and 10⁶ is treated as 999,000 rather than just _“three orders apart.”_

As magnitudes grow, linear distance overweights large scales and underweights small ones.
This causes the selection to favor higher prefixes (like **mega**) even when a value (like 50,000) clearly fits better under **kilo**.
In physical reasoning, a thousandfold difference should count equally regardless of where it occurs and **logarithmic distance** achieves that symmetry.

---

## 2. Defining the Unity-Distance

For a given value _x_ and candidate scale _s_, the unity-distance is defined as:

```
d(s, x) = | log₁₀(x / s) |
```

This measures how far _x_ is from **unity (1)** after being divided by the scale.

- If dividing by _s_ yields exactly 1, then _d = 0_ (perfect match).
- If _x/s = 10_ or _0.1_, the distance is 1 (one order of magnitude away).

This formulation directly expresses the idea: _“How close to 1 does this value become when scaled?”_

---

## 3. The Bias Factor: Human Perception of Overshoot

While logarithmic distance correctly measures proportional difference, human intuition distinguishes between **overshooting** and **undershooting** unity.

Describing 50,000 as _“fifty thousands”_ feels natural, while _“0.05 millions”_ feels wrong even though both are one order of magnitude apart.
To capture this asymmetry, the Unity-Distance Metric introduces a **bias factor**:

```
if ratio < 1:
    diff /= undershoot_bias   # undershoot_bias < 1
```

When the ratio `x/s < 1` (meaning the scale candidate is too large), the distance is **divided by a bias constant < 1**, penalizing undershoots more heavily.
This anchors the metric in _perceptual realism_ favoring scales yielding results slightly above 1 over those just below.

---

## 4. Why Log Base 10 Works for Binary Prefixes

Even though binary prefixes (kibi, mebi) use base 2, the base-10 logarithm remains effective because it measures **proportional magnitude**, not representation base.

Key insight:
`log₁₀(2¹⁰) ≈ 3` — meaning a binary thousand (1024) is roughly one decimal order above 10³.

Thus, log₁₀ space preserves the **relative alignment** between decimal and binary prefixes.
A suitable bias factor ensures that **1024** can be interpreted as either _kilo_ or _kibi_, depending on user preference — without distorting order relationships.

---

## 5. Summary

The Unity-Distance Metric offers a unified, perceptually accurate method for determining the most natural scale prefix.
By measuring distance in orders of magnitude and adjusting with a bias that reflects human expectation, it harmonizes **mathematical rigor** with **intuitive scale reasoning**.

Linear proximity is easy to compute, but logarithmic unity-distance expresses what users mean when they say:

> _“It’s about a thousand,”* or *“roughly a megabyte.”_
