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
[**wavelength_unit**=*string*]
[**spec_library**=*string*] [**spec_source_database**=*string*[,*string*,...]]
[**spec_dataset_id**=*string*[,*string*,...]] [**spec_similarity_method**=*string*]
[**spec_min_overlap_bands**=*value*] [**spec_top_n**=*value*]
[**-n**] [**-b**] [**-l**] [**-i**]

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

## SEE ALSO

*[i.hyper.speclookup](i.hyper.speclookup.md),
[i.hyper.lib_ecosis](i.hyper.lib_ecosis.md), [i.hyper.lib_usgs](i.hyper.lib_usgs.md),
[i.hyper.lib_relab](i.hyper.lib_relab.md),
[i.hyper.spectroscopy](i.hyper.spectroscopy.md), [i.hyper.import](i.hyper.import.md),
[i.hyper.geology](i.hyper.geology.md), [i.pysptools.unmix](i.pysptools.unmix.md),
[r3.to.rast](r3.to.rast.md), [m.proj](m.proj.md)*

## AUTHOR

Spectral Feature Extraction and Interpretation Engine
