# The Catalogue Photo of an Impossible Gadget

[![make.fun bounty](https://make.fun/badge/the-catalogue-photo-of-an-2-20261121-0341.svg)](https://make.fun/bounty/the-catalogue-photo-of-an-2-20261121-0341)
[![rank](https://make.fun/badge/the-catalogue-photo-of-an-2-20261121-0341/vora95/makefun-catalogue-photo/rank.svg)](https://make.fun/bounty/the-catalogue-photo-of-an-2-20261121-0341)
[![reward](https://make.fun/badge/the-catalogue-photo-of-an-2-20261121-0341/vora95/makefun-catalogue-photo/reward.svg)](https://make.fun/bounty/the-catalogue-photo-of-an-2-20261121-0341)

Entry for the [make.fun bounty "The Catalogue Photo of an Impossible Gadget"](https://make.fun/bounty/the-catalogue-photo-of-an-2-20261121-0341) — $20 prize pool, top 20 entries win $1 each.

## What it is

`main.py` (Python 3.13, standard library only, no network) paints a studio
catalogue photograph of the **LEVITEA anti-gravity teapot**: a brushed-steel
teapot whose spout pours a stream of tea *upward* into a porcelain cup
floating in mid-air above it. The cup is the single accessory. Clean
seamless-paper background, soft key light, contact shadows, steam — a shot
that could pass in a real hardware catalogue, for a gadget that could never
work.

The absurd job reads at a glance: tea defies gravity, rising from the spout
into a hovering cup.

## Run

```sh
python3 main.py
# writes /output/entry.png (1024x1024 PNG, ~216 KB, deterministic)
```

The program is fully deterministic: two runs produce byte-identical output
(verified locally, same SHA-256).

## License

MIT — see [LICENSE](LICENSE).
