# One input your precision model can't see

*Aditi Bombe · 8 September 2026*

Adriana — I've been checking coordinate precision in the graph and found something that affects the error model on your *"What a decimal place is actually worth"* slide. **The model itself is right, and so is your cap at 5 decimal places.** This is about one input it takes on trust.

## The assumption

Your table maps decimal places to positional error, which is exactly right for coordinates recorded in decimal degrees. But some of MinMod's coordinates were originally recorded in **degrees and minutes** and converted. For those, the decimal count is an artefact of the conversion and has nothing to do with how carefully the location was measured.

Here's a real record:

```
POINT (116.58333333333  71)
```

That's 116°35′ and 71°00′ — one reading, both axes measured to the nearest arcminute, about 1.2 km. But written out, the longitude carries 11 decimals and the latitude carries none. The table reads them as two completely different qualities of measurement when they're the same measurement.

## How often, and where

**5,288 records**, all in ten USGS commodity databases: `vms`, `carbonatite`, `podchrome`, `laterite`, `sedznpb`, `sedau`, `porcu`, `sedcu`, `ree` and `major-deposits`. In six of those, effectively *every* record is affected — `vms` and `carbonatite` are at 100%.

It's tightly contained. MRDS, which is three-quarters of the graph, is clean decimal degrees throughout — I used it as a control to check the detector wasn't inventing this, and it correctly identified 99.2–99.5% of MRDS as decimal degrees before I trusted any other result.

## Which way it goes, and by how much

I expected this to make the model too pessimistic. **It's mostly the other way, which is the direction that matters.**

Of the 10,576 axis readings in those records:

- **9,801 are treated as more precise than they are.** Because most converted values come out long — 11 to 15 decimals — your cap reads them as 5 dp, or ±0.7 m. The true precision is an arcminute, ±1.17 km. **The worst case is off by a factor of about 1,700**, and 2,760 readings are off by 100× or more.
- **775 are treated as less precise than they are**, which is the case I went looking for. `POINT (45 39.983333333333)` — that `45` is 45°00′, not a rounded whole degree. The table calls it ±70 km; it's really ±19.5 m. Worst case, 3,600×.
- **None are within 5% of right.**

Both happen in the same record, on different axes. Which one your model reports depends on which axis it reads — **and that's the one thing I couldn't check, because I was working from the three figures on your slide rather than the spreadsheet. Could you send it?** If the model takes the coarser axis it's over-cautious on these; if it takes the finer one it's over-confident. That changes which of the two numbers above is the one to worry about.

Against your own figures: **463** of these records have an axis at 1 decimal place or fewer, and **2,906** have different decimal counts on the two axes. (Both counts are on the underlying records rather than the merged sites your numbers use, so treat them as shape rather than a direct comparison.)

## The fix — an addition to your table, not a replacement

Before reading the decimal count, check whether the value sits exactly on a degrees-and-minutes grid:

```
if either axis is an exact arcminute  ->  ±1.17 km
if either axis is an exact arcsecond  ->  ±19.5 m
otherwise                             ->  your existing table, capped at 5 dp
```

Test with `abs(value * 60 - round(value * 60)) < 1e-8`, and the same with 3600 for arcseconds. Two details that matter:

- **Only test values with 6 or more decimals.** Below that the test passes automatically and means nothing — 0.3° × 60 = 18 exactly, so every 1-decimal value looks like an arcminute.
- **Check arcminutes before arcseconds.** Every arcminute value is also an exact arcsecond, so testing the other way round would credit the coarsest records with the finest precision.

Those ±1.17 km and ±19.5 m figures are on the same scale as your table, derived the same way from the grid size, so they drop straight in. (If you'd rather use half the grid spacing along one axis, it's ±0.93 km and ±15.4 m — the ratios are identical either way, it's just a convention choice.)

**What this recovers for you: 83 records** that your model currently rules out as too coarse for the 10 km blocking radius but which are actually precise enough to use. That's the smaller half of the story though — the bigger one is the 9,801 readings currently being trusted more than they deserve.

## One thing this can't fix

If a source published `37.90000`, it's stored as `37.9` and the trailing zeros are gone. Nothing recovers that from the stored value.

I can at least size it now. In a clean 5-decimal source you get a tidy cascade — `P9HTERGK` has 38,335 records at 5 decimals, 3,973 at 4, 386 at 3, 37 at 2, matching the ÷10-per-decimal pattern you'd predict almost exactly. So about 11% of values render short from lost zeros, but only ~0.12% land at 2 decimals or fewer. Small.

That cascade shape is also a useful test in itself: a source that *piles up* at one decimal count instead of cascading really is that coarse. `nicrpge` has 16,110 of its 17,954 records sitting at exactly 2 decimals — that's genuine ~1.1 km data, not a rendering artefact.

## The honest limit

There are **69,938 records where both axes are short** and nothing can be concluded either way — they might be converted, they might be decimal. I've left them unclassified rather than assume, because assuming they're decimal degrees would be the same mistake as the one this whole note is about, just pointing the other way. That includes the two biggest coarse sources, so it's not a small gap.

And the pairing logic — reading `71` as 71°00′ because its partner axis is clearly a conversion — is an inference, not a measurement. It's very probably right, but it's worth knowing it's an inference.

All of which is really an argument for the same thing: **the durable fix is recording precision when the coordinate is extracted**, while the source string is still there and `37.90000` still looks different from `37.9`. Everything here is reconstruction after the fact, and reconstruction has a floor.

Happy to walk through any of it, and I'll send the record IDs for the 5,288 if that's useful for spot-checking.
