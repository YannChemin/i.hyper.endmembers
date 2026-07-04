# i.hyper.endmembers

## NAME

*i.hyper.endmembers* - Extract spectral endmembers from a hyperspectral 3D
raster (PPI, N-FINDR, FIPPI, ATGP), optionally map their abundances, and
optionally identify each one against the shared *i.hyper.lib_\** spectral
library.

## SYNOPSIS

**i.hyper.endmembers**
**input**=*name* [**output**=*name*] [**output_file**=*name*]
[**output_format**=*string*] [**abundance_prefix**=*string*]
**n_endmembers**=*value* [**extraction_method**=*string*]
[**unmixing_method**=*string*] [**maxit**=*value*]
[**ppi_skewers**=*value*] [**random_seed**=*value*]
[**min_wavelength**=*value*] [**max_wavelength**=*value*]
[**max_invalid_fraction**=*value*]
[**wavelength_unit**=*string*]
[**spec_library**=*string*] [**spec_source_database**=*string*[,*string*,...]]
[**spec_dataset_id**=*string*[,*string*,...]] [**spec_similarity_method**=*string*]
[**spec_min_overlap_bands**=*value*] [**spec_min_overlap_fraction**=*value*]
[**spec_top_n**=*value*] [**plot_dir**=*string*]
[**-n**] [**-b**] [**-l**] [**-i**] [**-p**] [**-w**]

## DESCRIPTION

*i.hyper.endmembers* identifies the most spectrally "pure"/extreme pixels
(endmembers) in a hyperspectral 3D raster cube -- the classic first step of
a linear spectral unmixing workflow -- and reports their locations and
spectra. Unlike *i.pysptools.unmix*, which works on a 2D imagery group,
this module reads directly from a GRASS 3D raster (as produced by
*i.hyper.import*), and follows the same band-metadata and region-handling
conventions as the rest of the `i.hyper.*` family.

Endmember extraction needs the whole scene loaded at once (unlike
per-pixel classification, it searches for extremes across the full image),
so processing is not chunked; keep the computational region to your actual
area of interest.

### Extraction methods

- **ATGP** (Automatic Target Generation Process): starts from the
  pixel with maximum spectral norm, then repeatedly picks the pixel with
  the largest residual after projecting out the subspace spanned by the
  endmembers already found. Fast and deterministic.
- **NFINDR** (default): reduces the cube to *p*-1 dimensions via PCA
  (*p* = n_endmembers) and iteratively swaps candidate endmembers to
  maximize the volume of the simplex they form -- the classic algorithm.
  Initialized from ATGP by default (`-n` to use a random start instead).
- **FIPPI**: a Fast Iterative Pixel Purity Index, in the spirit of Chang &
  Plaza (2006) -- alternates between projecting the cube onto random and
  endmember-derived skewer directions and refining the candidate set until
  it stops changing.
- **PPI** (Pixel Purity Index): projects every pixel onto many random
  directions in band space and scores each pixel by how often it lands at
  a projection extremum. The only method that can extract more endmembers
  than there are bands.

PPI and FIPPI runtime scales with **ppi_skewers** and the number of valid
pixels. Lower **ppi_skewers** for a quicker, less statistically robust
estimate. (This is dominated by dense matrix multiplication, so it also
benefits substantially from an optimized BLAS -- e.g. OpenBLAS rather than
the plain reference BLAS some distributions ship by default.)

### Outputs

- **output**: a point vector map, one point per endmember, with one
  attribute column per band named after its central wavelength (e.g.
  `wl_2265_19`), holding that endmember's reflectance at that band.
- **output_file**: the same spectra as CSV or JSON (**output_format**).
  The first two fields are the endmember's native projected X,Y by
  default, or longitude/latitude (WGS84) if **-l** is given -- reprojected
  via `m.proj`, so this works from any source CRS, not just geographic
  locations.
- **abundance_prefix**: if given, also unmixes the *whole* scene against
  the extracted endmembers (**unmixing_method**) and writes one abundance
  raster per endmember (`<prefix>_1`, `<prefix>_2`, ...).

At least one of **output** / **output_file** is required.

### Unmixing methods

- **UCLS**: unconstrained least squares (fastest, no constraints).
- **NNLS**: non-negativity-constrained least squares.
- **FCLS** (default): fully constrained (non-negative *and* sums to one),
  via the standard trick of augmenting the system with a large-weight row
  enforcing the sum-to-one constraint and solving as NNLS (Heinz & Chang,
  2001) -- gives an exact-constraint result without needing a general QP
  solver such as cvxopt.

### Band metadata and compatibility

Band wavelength/FWHM/validity metadata is read the same way as
*i.hyper.spectroscopy*: from `i.hyper.import`'s `grid3/<map>/hyper.json`
sidecar if present, else `r3.info -h` history, else per-band `r.support`
metadata. Use **-b** to restrict processing to bands marked valid (`valid=1`)
in that metadata, and **min_wavelength**/**max_wavelength** to restrict to a
spectral sub-range (e.g. to exclude noisy detector edges or strong water-
vapor absorption windows), consistent with *i.hyper.geology*'s convention.

### Automatic exclusion of out-of-range bands (max_invalid_fraction)

`-b`/**min_wavelength**/**max_wavelength** rely on the cube's own
metadata (or the caller) already knowing which bands are unreliable.
That is not always true: a real EMIT scene's per-band `valid=1` metadata
did not flag two bands at ~1357nm and ~1417nm (classic strong
water-vapor-absorption wavelengths) even though 61.7% and 28.1% of valid
pixels there held a physically impossible out-of-range (outside 0.0-1.0)
reflectance value -- a sensor/atmospheric-correction artifact, not a
measurement.

This matters more for extraction than it might seem: ATGP starts from
the pixel with the single largest spectral vector norm, and N-FINDR/PPI/
FIPPI all likewise select or refine endmembers by norm or simplex volume.
An out-of-range value in even one band inflates that pixel's norm and
can change which pixel looks most "extreme" -- and because endmember
algorithms specifically hunt for rare/extreme pixels, even a
low-frequency artifact (one real case found here: just 0.14% of pixels
in a third band) is disproportionately likely to land on exactly the
pixels selected as endmembers, not average out harmlessly. Verified
directly on this scene: excluding the two worst bands changed 2 of 6
ATGP-selected pixels, including the very first (max-norm) pick.

**max_invalid_fraction** (default 0.0) guards against this independent
of `-b`/wavelength range/upstream metadata: after loading the cube, any
band where more than this fraction of valid pixels has a value outside
0.0-1.0 is excluded entirely -- from extraction, identification, and
plotting -- with a warning naming the wavelength and the fraction
affected. The default of 0 (exclude on even a single contaminated pixel)
is deliberately strict, for the reason above; raise it (e.g. to 0.01) if
your sensor is known to have harmless, genuinely sparse per-pixel noise
unrelated to a systematic band-level artifact. Set to 1.0 to disable
entirely.

### Identification against the shared spectral library (-i)

**-i** identifies every extracted endmember against the shared local
spectral library built by *i.hyper.lib_ecosis*/*i.hyper.lib_usgs*/
*i.hyper.lib_relab*, by calling *i.hyper.speclookup* directly -- one real
GRASS module invocation covering all endmembers at once (each endmember
becomes one query row in a temporary CSV, and *i.hyper.speclookup* already
ranks one result set per row), not a reimplementation of its matching
logic. This is the natural second step after extraction: N-FINDR/ATGP/PPI/
FIPPI tell you *where* the spectrally distinct materials in a scene are;
**-i** gives each one a candidate real-world identity.

Before being written to that query CSV, each endmember's own values are
checked against the physical reflectance range: any value outside
0.0-1.0 (e.g. a water-vapor-absorption-band retrieval artifact -- the
same kind of spike the plot's fixed y-axis clips from view) is left blank
in that row rather than passed through as-is or written as a literal
`nan`. A blank CSV cell is skipped cleanly by *i.hyper.speclookup*'s own
reader (`float('')` raises, same as any other unparseable value), simply
dropping that one band from that endmember's query -- whereas writing
the literal text `nan` would not be caught (Python's `float()` parses the
strings `"nan"`/`"inf"` successfully instead of raising, the same pitfall
already fixed in the harvesters' own ingestion), and passing the raw
out-of-range value through uncorrected would silently distort the SAM/
correlation/Euclidean computation for every candidate compared against
that endmember. This is not a cosmetic fix: on a real EMIT scene, a
handful of such artifact values changed which library record several
endmembers matched best, in one case improving the best match from
`sam=55.7` (a poor fit) to `sam=9.4` (a much better one) once the
corrupting values were excluded from the comparison.

- **spec_source_database=**, **spec_dataset_id=**: narrow the search (e.g.
  to `usgs_splib07`'s mineral chapters for a geology scene, or `relab`'s
  `Rock`/`Mineral` categories) -- the same filters *i.hyper.speclookup*
  itself takes, and for the same reason: matching against the full
  ~266,000-record library takes minutes, matching against one relevant
  source/category takes seconds.
- **spec_similarity_method=** (default `sam`, matching
  *i.hyper.speclookup*'s own default): Spectral Angle Mapper is usually
  the right choice here specifically because it is insensitive to a
  uniform brightness/albedo offset between a real scene endmember (subject
  to atmospheric and BRDF effects) and a clean lab/field reference
  spectrum.
- **spec_top_n=** (default 3): only the single best match is attached to
  the output, but requesting more than one candidate lets a **confidence
  margin** to the runner-up be computed -- a small margin means the top
  match was only narrowly better than the next-best candidate (e.g. two
  visually similar minerals), a large margin means it was a clear winner.
- **spec_min_overlap_bands=** (default 5, absolute) and
  **spec_min_overlap_fraction=** (default 0.55, relative to the cube's
  own band count): both must be satisfied for a candidate to be
  considered at all. This matters more than it might look: some USGS
  NIC4/Nicolet mineral records are only measured from ~2400nm onward, so
  against a typical ~250-band VNIR/SWIR cube they only overlap in a
  narrow sliver of a dozen or so bands at the very edge of the range --
  technically above the old bands-only default of 5, but far too little
  evidence to trust a mineral identification from. The 0.55 default
  requires a clear majority (more than half) of the cube's bands to
  actually overlap before a match is trusted, rather than reporting a
  low-confidence match as if it were a strong one.

Each identified endmember is labeled with the best match's **source
database**, **dataset**, **record ID**, **title**, **organization**, the
**similarity score** (accuracy) and **number of overlapping bands** used
to compute it, and the **confidence margin** to the runner-up (precision)
-- attached to the vector map's attribute table (`match_source`,
`match_dataset`, `match_record`, `match_title`, `match_organization`,
`match_score`, `match_overlap_bands`, `match_margin`) and, more fully, to
**output_file** (the same fields plus `match_method` and the matched
record's complete `match_extra_metadata` JSON -- mineral/plant name,
formula, collection locality, and everything else the source harvester
captured). An endmember with no library candidate above
**spec_min_overlap_bands** gets a blank/null match rather than a
fabricated one.

### Plotting (-p / -w)

**-p** renders **two** separate PNGs, deliberately not one crowded overlay:

1. **Extracted endmember spectra**: every endmember's own spectrum
   together, each a distinct color, numbered both in the legend and
   directly at the end of its curve (so individual endmembers can be told
   apart at a glance without hunting through the legend on a busy plot).
2. **Identified reference spectra**: (only written if **-i** was also
   given and at least one match was found) every identified library
   match's own spectrum together, using the *same* color/number as its
   endmember in graph 1 -- each legend entry gives the match's full
   identity (title, record ID, source database), its similarity score,
   and the number of overlapping bands the score was computed from. A
   numeric score alone is not enough to trust an identification; seeing
   the actual reference spectrum's shape (and how many bands really
   overlapped) is what graph 2 is for.

Both axes are fixed the same way in both plots: the y-axis to 0.0-1.0
(the physical range of a reflectance value -- any excursion in the
underlying data, e.g. a water-vapor-absorption-band retrieval artifact,
is a known data-quality issue and is simply clipped from view rather than
rescaling the whole plot), and the x-axis to the endmember's own
wavelength range, even when a matched library record natively covers a
much wider one -- e.g. a Nicolet FTIR reference extending to 200,000+ nm
would otherwise squeeze the whole comparison into an unreadable sliver.

Both PNGs are written to **plot_dir** (default: the current GRASS
location's own directory, `$GISDBASE/$LOCATION_NAME/` -- so they land
alongside whatever project the input raster belongs to without needing to
specify one explicitly), named entirely by the module itself -- there is
no option to set the filenames individually, only the directory:
`<output>_spectra.png` and `<output>_reference_spectra.png` (or
`<input>_endmembers_spectra.png`/`<input>_endmembers_reference_spectra.png`
if no vector **output** was requested). Add **-w** to also open both in
an interactive window (needs a display; the files are still written
either way). **-p** alone (without **output**/**output_file**) is a
valid, plot-only invocation.

## NOTES

Column/field names are derived from each band's central wavelength, in
**wavelength_unit** (nm by default), sanitized into valid SQL identifiers
(e.g. `2265.19` nm becomes `wl_2265_19`).

Endmember coordinates are cell centers of whichever pixel was selected,
computed directly from the active computational region -- they are exact
regardless of the region's resolution or extent relative to the raster's
native footprint.

## EXAMPLES

The examples below use an EMIT scene imported with *i.hyper.import* into
its own location, `emit_slovakia` (raster_3d map `emit_20240730`, 244
bands, `hyper.json` sidecar metadata). Its native footprint covers nearly
all of Slovakia (1727 x 2746 pixels, north=49.10 south=48.17 east=20.53
west=19.04) -- endmember extraction needs the whole active region loaded
into memory at once (see above), so the *first* step in any real session
is always to restrict the region to the actual area of interest, not run
against the full native extent:

```sh
g.region n=48.70 s=48.60 e=19.80 w=19.70 res=0:00:01.952037
g.region -g
```

```text
projection=3
zone=0
n=48.7
s=48.6
w=19.7
e=19.8
nsres=0.000543478260869573
ewres=0.000543478260869573
rows=184
cols=184
cells=33856
```

### Example 1: N-FINDR (default), vector map + CSV with longitude/latitude

```sh
i.hyper.endmembers input=emit_20240730 output=slovakia_endmembers \
    output_file=slovakia_endmembers.csv -l n_endmembers=6 \
    extraction_method=NFINDR
```

```text
Extracting 244 bands (184x184 pixels)…
Extracting 6 endmembers using NFINDR…
Writing endmember vector map → slovakia_endmembers…
Writing endmember spectra (csv) → slovakia_endmembers.csv…
Done: 6 endmember(s) extracted with NFINDR.
```

The vector map has one point per endmember and one attribute column per
band, named by its central wavelength:

```sh
v.info -c map=slovakia_endmembers
```

```text
INTEGER|cat
DOUBLE PRECISION|x
DOUBLE PRECISION|y
DOUBLE PRECISION|wl_381_0056
DOUBLE PRECISION|wl_388_4092
DOUBLE PRECISION|wl_395_8158
...
```

And the CSV (`-l` puts longitude/latitude first, reprojected via `m.proj`
from this location's native CRS -- here already geographic, so the values
are unchanged, but the same flag reprojects correctly from a projected/UTM
location too):

```text
lon,lat,wl_381_0056,wl_388_4092,wl_395_8158,wl_403_2254,...
19.70027174,48.62038043,0.00179211446,0.00183079974,0.00186951912,0.00190832582,...
```

### Example 2: PPI + FCLS abundance mapping over the whole region

```sh
i.hyper.endmembers input=emit_20240730 output=slovakia_ppi \
    n_endmembers=5 extraction_method=PPI \
    abundance_prefix=slovakia_abund unmixing_method=FCLS random_seed=42
```

```text
Extracting 244 bands (184x184 pixels)…
Extracting 5 endmembers using PPI…
Writing endmember vector map → slovakia_ppi…
Unmixing abundances using FCLS…
Done: 5 endmember(s) extracted with PPI.
```

This writes `slovakia_abund_1` .. `slovakia_abund_5`, one abundance raster
per endmember, each valued 0-1 and summing to 1 across the five rasters at
every pixel (FCLS's non-negativity + sum-to-one constraints):

```sh
r.univar map=slovakia_abund_1 -g
```

```text
n=33856
min=0
max=1
mean=0.0485496587901701
```

### Example 3: restrict to valid bands in a wavelength range, export JSON

```sh
i.hyper.endmembers input=emit_20240730 output=slovakia_endmembers_b \
    output_file=slovakia_endmembers.json output_format=json \
    n_endmembers=8 extraction_method=ATGP \
    -b min_wavelength=450 max_wavelength=2400
```

```text
Extracting 221 bands (184x184 pixels)…
Extracting 8 endmembers using ATGP…
Writing endmember vector map → slovakia_endmembers_b…
Writing endmember spectra (json) → slovakia_endmembers.json…
Done: 8 endmember(s) extracted with ATGP.
```

221 of the cube's 244 bands fall in the requested 450-2400nm range; no
`-l` here, so the JSON's first two fields are the native projected X,Y
(this location happens to be geographic, so numerically these look like
lon/lat too, but for a projected/UTM location they would not be):

```json
[
  {
    "x": 19.78233695652174,
    "y": 48.674728260869564,
    "wl_455_1703": 0.0431,
    "wl_462_5989": 0.0448,
    ...
  },
  ...
]
```

### Example 4: identify each endmember against the shared spectral library

```sh
i.hyper.endmembers input=emit_20240730 output=slovakia_endmembers_id \
    output_file=slovakia_endmembers_id.csv -l -i n_endmembers=6 \
    extraction_method=NFINDR spec_source_database=usgs_splib07 \
    spec_dataset_id=ChapterV_Vegetation,ChapterM_Minerals,ChapterS_SoilsAndMixtures
```

```text
Extracting 244 bands (184x184 pixels)…
Extracting 6 endmembers using NFINDR…
Identifying endmembers against the shared spectral library (i.hyper.speclookup)…
Identified 6 of 6 endmember(s) (method=sam).
Endmember 1: Vegetation (splib07a_LeafySpurge_Spurge-A2-Jun98_ASDFRa_AREF, usgs_splib07) -- sam=5.18419, margin=0.02959 (240 overlapping bands)
Endmember 2: Vegetation (splib07a_Marsh_SCAM50%..._CRMS121v32_ASDFRa_AREF, usgs_splib07) -- sam=3.71498, margin=0.2749 (234 overlapping bands)
Endmember 3: Vegetation (splib07a_LeafySpurge_Spurge-A1-Oct97_ASDFRa_AREF, usgs_splib07) -- sam=3.4407, margin=0.03746 (240 overlapping bands)
Endmember 4: Vegetation (splib07a_Marsh_SCAM50%..._CRMS121v32_ASDFRa_AREF, usgs_splib07) -- sam=1.37321, margin=0.1085 (234 overlapping bands)
Endmember 5: Vegetation (splib07a_Oak_QUDU_CA01-QUDU-1_bush_1_ASDFRa_AREF, usgs_splib07) -- sam=1.7603, margin=0.1107 (236 overlapping bands)
Endmember 6: Vegetation (splib07a_Grass-Smoothbrome_YNP-SB-1_AVIRISb_RTGC, usgs_splib07) -- sam=3.79253, margin=0.2401 (237 overlapping bands)
Writing endmember vector map → slovakia_endmembers_id…
Writing endmember spectra (csv) → slovakia_endmembers_id.csv…
Done: 6 endmember(s) extracted with NFINDR.
```

Genuinely sensible for this Slovakia forest scene: every endmember matches
best against USGS's Vegetation chapter, not Minerals or Soils, despite all
three being searched. The vector map's attribute table carries the
identity and confidence fields directly:

```sh
v.db.select map=slovakia_endmembers_id columns=cat,match_title,match_record,match_score,match_overlap_bands,match_margin
```

```text
cat|match_title|match_record|match_score|match_overlap_bands|match_margin
1|Vegetation|splib07a_LeafySpurge_Spurge-A2-Jun98_ASDFRa_AREF|5.184195|240|0.029587
2|Vegetation|splib07a_Marsh_SCAM50%..._CRMS121v32_ASDFRa_AREF|3.714981|234|0.274929
...
```

and the CSV additionally carries the full `match_extra_metadata` for the
top match, e.g. for endmember 1:

```text
{"documentation_format": "PLANT", "sample_id": "Spurge-A2-Jun98",
 "plant_type": "Invasive herbaceous perennial weed", "plant": "Leafy spurge",
 "latin_name": "Euphorbia esula L.", "collection_locality": "Golden, Colorado", ...}
```

### Example 5: identify and plot, on a real EMIT scene (emit_dubai)

Using the `emit_dubai` project's own `AlMarwanProjectSite` saved region
and its `emit_20260623` cube (255 bands):

```sh
g.region region=AlMarwanProjectSite
i.hyper.endmembers input=emit_20260623 output=dubai_endmembers \
    -i -p -b n_endmembers=6 extraction_method=NFINDR \
    spec_source_database=usgs_splib07
```

```text
Extracting 255 bands (350x706 pixels)…
WARNING: Excluding band at 1357.2nm from endmember extraction: 61.7% of
         valid pixels have an out-of-range (outside 0.0-1.0) reflectance
         value (max_invalid_fraction=0).
WARNING: Excluding band at 1416.8nm from endmember extraction: 28.1% of
         valid pixels have an out-of-range (outside 0.0-1.0) reflectance
         value (max_invalid_fraction=0).
WARNING: Excluding band at 1439.1nm from endmember extraction: 0.1% of
         valid pixels have an out-of-range (outside 0.0-1.0) reflectance
         value (max_invalid_fraction=0).
Extracting 6 endmembers using NFINDR…
Identifying endmembers against the shared spectral library (i.hyper.speclookup)…
Identified 6 of 6 endmember(s) (method=sam).
Endmember 1: Vegetation (splib07a_Rangeland_L02-045_S01%_G04%_ASDFRa_AREF, usgs_splib07) -- sam=4.0643, margin=0.06403 (247 overlapping bands)
Endmember 2: Organic Compounds (splib07a_Xanthine_SA-X0626_90K_NIC4aa_RREF, usgs_splib07) -- sam=11.6209, margin=0.5861 (152 overlapping bands)
Endmember 3: Liquids (splib07a_Water+Montmor_SWy-2+5.01g-l_ASDFRa_AREF, usgs_splib07) -- sam=12.8549, margin=3.96 (252 overlapping bands)
Endmember 4: Vegetation (splib07a_Marsh_sediment_DWV3-0511_dry_ASDFRa_AREF, usgs_splib07) -- sam=5.36816, margin=0.4425 (242 overlapping bands)
Endmember 5: Organic Compounds (splib07a_Peptidogylcan_SA-69554_ASDFRa_AREF, usgs_splib07) -- sam=5.96867, margin=0.3165 (252 overlapping bands)
Endmember 6: Minerals (splib07a_Vesuvianite_HS446.1B_Idocras_ASDFRa_AREF, usgs_splib07) -- sam=2.86591, margin=0.01122 (252 overlapping bands)
Wrote endmember spectra plot → /home/yann/grassdata/emit_dubai/dubai_endmembers_spectra.png
Wrote reference spectra plot → /home/yann/grassdata/emit_dubai/dubai_endmembers_reference_spectra.png
Writing endmember vector map → dubai_endmembers…
Done: 6 endmember(s) extracted with NFINDR.
```

No **output_file**/**plot_dir** given here, so both PNGs land in the
project's own directory automatically
(`$GISDBASE/$LOCATION_NAME/` = `~/grassdata/emit_dubai/`), named entirely
by the module from the vector output name. `dubai_endmembers_spectra.png`
shows the six extracted endmembers together, numbered;
`dubai_endmembers_reference_spectra.png` shows their six identified USGS
matches together, same numbers/colors, each labeled with its full
identity and score.

This run also demonstrates why **max_invalid_fraction**'s strict default
(0) matters at the *extraction* stage, not just identification: with the
two worst contaminated bands (and one marginal one, at just 0.14% of
pixels) excluded before ATGP/N-FINDR ever run, different pixels get
selected as endmembers than in an earlier run where those bands were left
in -- confirmed directly by comparing the raw ATGP pixel indices with and
without the bands excluded (2 of 6 changed, including the very first
max-norm pick). The endmember spectra plot is also visibly cleaner: no
more multiple-hundred-percent reflectance spike near 1350-1450nm, since
the pixels now selected were never chosen partly *because of* that
artifact in the first place.

## SEE ALSO

*[i.hyper.speclookup](i.hyper.speclookup.md),
[i.hyper.lib_ecosis](i.hyper.lib_ecosis.md), [i.hyper.lib_usgs](i.hyper.lib_usgs.md),
[i.hyper.lib_relab](i.hyper.lib_relab.md),
[i.hyper.spectroscopy](i.hyper.spectroscopy.md), [i.hyper.import](i.hyper.import.md),
[i.hyper.geology](i.hyper.geology.md), [i.pysptools.unmix](i.pysptools.unmix.md),
[r3.to.rast](r3.to.rast.md), [m.proj](m.proj.md)*

## AUTHOR

Spectral Feature Extraction and Interpretation Engine
