#!/usr/bin/env python
##############################################################################
# MODULE:    i.hyper.endmembers
# AUTHOR(S): Spectral Feature Extraction and Interpretation Engine
# PURPOSE:   Extract spectral endmembers from a hyperspectral 3D raster using
#            PPI, N-FINDR, FIPPI or ATGP, export them as a vector map (with
#            per-band reflectance attributes named by wavelength) and/or as
#            CSV/JSON, and optionally map their abundances (FCLS/UCLS/NNLS).
# COPYRIGHT: (C) 2026 by the GRASS Development Team
# SPDX-License-Identifier: GPL-2.0-or-later
##############################################################################

# %module
# % description: Extract spectral endmembers from a hyperspectral 3D raster (PPI, N-FINDR, FIPPI, ATGP) and optionally map their abundances
# % keyword: imagery
# % keyword: hyperspectral
# % keyword: endmember
# % keyword: spectral unmixing
# %end

# %option G_OPT_R3_INPUT
# % key: input
# % required: yes
# % description: Input hyperspectral 3D raster map
# % guisection: Input
# %end

# %option G_OPT_V_OUTPUT
# % key: output
# % required: no
# % description: Output vector map of endmember locations (attributes named by wavelength)
# % guisection: Output
# %end

# %option G_OPT_F_OUTPUT
# % key: output_file
# % required: no
# % description: Output endmember spectra as CSV or JSON (first two columns/fields: X,Y, or lon,lat with -l)
# % guisection: Output
# %end

# %option
# % key: output_format
# % type: string
# % required: no
# % options: csv,json
# % answer: csv
# % description: Format for output_file
# % guisection: Output
# %end

# %option
# % key: abundance_prefix
# % type: string
# % required: no
# % description: Prefix for per-endmember abundance raster maps (enables spectral unmixing over the whole scene)
# % guisection: Output
# %end

# %option
# % key: n_endmembers
# % type: integer
# % required: yes
# % description: Number of endmembers to extract
# % guisection: Extraction
# %end

# %option
# % key: extraction_method
# % type: string
# % required: no
# % options: FIPPI,PPI,NFINDR,ATGP
# % answer: NFINDR
# % description: Endmember extraction algorithm
# % guisection: Extraction
# %end

# %option
# % key: unmixing_method
# % type: string
# % required: no
# % options: FCLS,UCLS,NNLS
# % answer: FCLS
# % description: Spectral unmixing algorithm (used only with abundance_prefix)
# % guisection: Extraction
# %end

# %option
# % key: maxit
# % type: integer
# % required: no
# % description: Maximum refinement iterations for NFINDR/FIPPI (default: 3x number of bands)
# % guisection: Extraction
# %end

# %option
# % key: ppi_skewers
# % type: integer
# % required: no
# % answer: 10000
# % description: Number of random skewer directions for PPI/FIPPI (runtime scales linearly with this)
# % guisection: Extraction
# %end

# %option
# % key: random_seed
# % type: integer
# % required: no
# % description: Random seed for PPI/FIPPI/random-initialization steps (for reproducibility)
# % guisection: Extraction
# %end

# %option
# % key: min_wavelength
# % type: double
# % required: no
# % description: Restrict processing to bands at or above this wavelength (nm)
# % guisection: Bands
# %end

# %option
# % key: max_wavelength
# % type: double
# % required: no
# % description: Restrict processing to bands at or below this wavelength (nm)
# % guisection: Bands
# %end

# %option
# % key: wavelength_unit
# % type: string
# % required: no
# % options: nm,um
# % answer: nm
# % description: Unit used for wavelength-based attribute/column names (values themselves are always reflectance)
# % guisection: Output
# %end

# %option
# % key: spec_library
# % type: string
# % required: no
# % description: Shared spectral library root to identify endmembers against (default: i.hyper.speclookup's own default, $HOME/grassdata/hyperspeclib, as built by i.hyper.lib_ecosis/i.hyper.lib_usgs/i.hyper.lib_relab). Only used with -i
# % guisection: Identification
# %end

# %option
# % key: spec_source_database
# % type: string
# % required: no
# % multiple: yes
# % description: Restrict identification to specific harvested sources (e.g. usgs_splib07,relab; default: all). Only used with -i
# % guisection: Identification
# %end

# %option
# % key: spec_dataset_id
# % type: string
# % required: no
# % multiple: yes
# % description: Restrict identification to specific dataset_id values (a USGS chapter, RELAB category, or EcoSIS package ID; default: all). Only used with -i
# % guisection: Identification
# %end

# %option
# % key: spec_similarity_method
# % type: string
# % required: no
# % options: sam,correlation,euclidean
# % answer: sam
# % description: Spectral similarity metric used for identification (see i.hyper.speclookup). Only used with -i
# % guisection: Identification
# %end

# %option
# % key: spec_min_overlap_bands
# % type: integer
# % required: no
# % answer: 5
# % description: Minimum overlapping bands required to consider a library candidate during identification (absolute floor). Only used with -i
# % guisection: Identification
# %end

# %option
# % key: spec_min_overlap_fraction
# % type: double
# % required: no
# % answer: 0.55
# % description: Minimum overlapping bands required, as a fraction (0-1) of the cube's own band count -- both this and spec_min_overlap_bands must be satisfied. An absolute floor alone does not scale to a hyperspectral cube: e.g. 13 overlapping bands is a weak, edge-of-range match out of 255 EMIT bands. Default requires a majority (>50%) of the cube's bands to be covered before a match is trusted. Only used with -i
# % guisection: Identification
# %end

# %option
# % key: spec_top_n
# % type: integer
# % required: no
# % answer: 3
# % description: Number of ranked library candidates to request per endmember during identification (only the best match is attached, but >1 lets a confidence margin to the runner-up be reported). Only used with -i
# % guisection: Identification
# %end

# %flag
# % key: i
# % description: Identify each endmember against the shared i.hyper.lib_* spectral library (via i.hyper.speclookup) and label it with the best match's metadata, similarity score, and a confidence margin to the runner-up
# % guisection: Identification
# %end

# %flag
# % key: p
# % description: Plot the extracted endmember spectra (PNG; labeled with their identified library match if -i is also given -- solid line is the extracted endmember, dashed line its matched reference spectrum)
# % guisection: Plot
# %end

# %flag
# % key: w
# % description: Also display the endmember spectra plot in an interactive window (requires -p and a display)
# % guisection: Plot
# %end

# %option
# % key: plot_dir
# % type: string
# % required: no
# % description: Directory to save the endmember spectra plot PNG (default: the current GRASS location's own directory, e.g. $GISDBASE/$LOCATION_NAME/). Only used with -p
# % guisection: Plot
# %end

# %flag
# % key: n
# % description: Disable ATGP-based initialization for NFINDR (no effect on other methods)
# % guisection: Extraction
# %end

# %flag
# % key: b
# % description: Only use bands marked as valid (valid=1) in metadata
# % guisection: Bands
# %end

# %flag
# % key: l
# % description: Use longitude/latitude (WGS84) instead of native X/Y as the first two fields in output_file
# % guisection: Output
# %end


from __future__ import annotations

import os
import sys
import atexit
import json as json_module
import csv as csv_module
from typing import Optional

import numpy as np
import grass.script as gs

# ---------------------------------------------------------------------------
# Temp raster cleanup
# ---------------------------------------------------------------------------

_TMP_RASTERS: list[str] = []


def _cleanup_tmp_rasters():
    if _TMP_RASTERS:
        gs.run_command('g.remove', type='raster',
                       name=','.join(_TMP_RASTERS), flags='f', quiet=True)


atexit.register(_cleanup_tmp_rasters)

# ---------------------------------------------------------------------------
# 3D raster Z-slice extraction
# ---------------------------------------------------------------------------
#
# Uses the standard r3.to.rast module, windowing the 3D region to a single
# depth slice, rather than a custom ctypes fast-path: r3.to.rast is stable
# for a region that is a sub-window of the raster's native footprint (a
# hand-rolled ctypes extraction was found to corrupt memory in exactly that
# case while developing i.hyper.spectroscopy) and self-reconciles any 2D/3D
# region mismatch.


def extract_band(raster3d: str, band_num: int) -> str:
    """Extract band_num (1-based) from raster3d into a temporary 2D raster.

    Returns the temporary 2D raster name (registered for cleanup at exit).
    """
    z = band_num - 1  # 1-based → 0-based
    base = raster3d.replace('@', '_').replace('#', '_').replace('.', '_')
    tmp_prefix = f"tmp_endmembers_{base}_{band_num}"
    tmp_name = f"{tmp_prefix}_00001"  # r3.to.rast's single-slice output suffix

    saved = gs.parse_command('g.region', flags='3g')
    gs.run_command('g.region', b=z, t=z + 1, tbres=1)
    try:
        gs.run_command('r3.to.rast', input=raster3d, output=tmp_prefix,
                       overwrite=True, quiet=True)
    finally:
        gs.run_command('g.region', b=saved['b'], t=saved['t'],
                       tbres=saved['tbres'])

    _TMP_RASTERS.append(tmp_name)
    return tmp_name

# ---------------------------------------------------------------------------
# Band metadata (mirrors i.hyper.spectroscopy's get_band_info, for
# compatibility with cubes imported via i.hyper.import / i.hyper.* tools)
# ---------------------------------------------------------------------------


def _load_hyper_json_bands(raster3d: str) -> list[dict]:
    """Read wavelength/fwhm/validity from i.hyper.import's JSON sidecar.

    i.hyper.import (HyperMetadata) stores band metadata at
    $MAPSET/grid3/<mapname>/hyper.json rather than in r3.support history,
    so that must be checked before falling back to r3.info/r.support.
    """
    name, mapset = (raster3d.split('@', 1) if '@' in raster3d
                     else (raster3d, None))
    try:
        env = gs.gisenv()
        mapset = mapset or env['MAPSET']
        path = os.path.join(env['GISDBASE'], env['LOCATION_NAME'], mapset,
                            'grid3', name, 'hyper.json')
    except Exception:
        return []

    if not os.path.isfile(path):
        return []

    with open(path) as _fj:
        data = json_module.load(_fj)

    b = data.get('bands') or {}
    wavelengths = b.get('wavelength')
    if not wavelengths:
        return []
    fwhms = b.get('fwhm') or []
    valids = b.get('validity') or []

    bands = []
    for i, wl in enumerate(wavelengths):
        bands.append({
            'band': i + 1,
            'wavelength': float(wl),
            'fwhm': float(fwhms[i]) if i < len(fwhms) else 10.0,
            'valid': bool(valids[i]) if i < len(valids) else True,
        })
    return bands


def get_band_info(raster3d: str, only_valid: bool = False) -> list[dict]:
    """Return sorted list of {band, wavelength, fwhm, valid} dicts.

    Primary source is i.hyper.import's grid3/<map>/hyper.json sidecar.
    Falls back to r3.info -h history (format: 'Band N: W nm, FWHM: F nm'),
    then to r.support metadata per band if history is missing.
    """
    json_bands = _load_hyper_json_bands(raster3d)
    if json_bands:
        json_bands.sort(key=lambda b: b['wavelength'])
        if only_valid:
            json_bands = [b for b in json_bands if b['valid']]
            if not json_bands:
                gs.fatal("No valid bands found (all marked valid=0).")
        return json_bands

    info = gs.raster3d_info(raster3d)
    depths = int(info['depths'])

    bands: list[dict] = []

    # Primary: parse r3.info history
    try:
        history = gs.read_command('r3.info', flags='h', map=raster3d)
        for line in history.split('\n'):
            line = line.strip()
            if not line.startswith('Band '):
                continue
            try:
                parts = line.split('Band ')[1].split(':')
                band_num = int(parts[0].strip())
                wavelength = float(parts[1].split('nm')[0].strip())
                fwhm_str = parts[2].split('nm')[0].strip() if len(parts) > 2 else '10'
                fwhm = float(fwhm_str) if fwhm_str else 10.0
                bands.append({'band': band_num, 'wavelength': wavelength,
                               'fwhm': fwhm, 'valid': True})
            except (ValueError, IndexError):
                pass
    except Exception:
        pass

    # Fallback: r.support per-band metadata
    if not bands:
        gs.verbose("No band info in r3.info history; trying r.support per band")
        for i in range(1, depths + 1):
            band_name = f"{raster3d}#{i}"
            wl = fwhm = None
            valid = True
            unit = 'nm'
            try:
                result = gs.read_command('r.support', map=band_name, flags='n')
                for ln in result.split('\n'):
                    ln = ln.strip()
                    if ln.startswith('wavelength='):
                        wl = float(ln.split('=')[1])
                    elif ln.startswith('FWHM='):
                        fwhm = float(ln.split('=')[1])
                    elif ln.startswith('valid='):
                        valid = int(ln.split('=')[1]) == 1
                    elif ln.startswith('unit='):
                        unit = ln.split('=')[1].strip()
            except Exception:
                pass
            if wl is None:
                continue
            unit = unit.lower()
            if unit in ('um', 'µm', 'micrometer', 'micron'):
                wl *= 1000.0
            elif unit in ('m', 'meter'):
                wl *= 1e9
            bands.append({'band': i, 'wavelength': wl,
                          'fwhm': fwhm or 10.0, 'valid': valid})

    if not bands:
        gs.fatal(
            f"No wavelength metadata in '{raster3d}'. "
            "Import data with i.hyper.import or add wavelength metadata."
        )

    bands.sort(key=lambda b: b['wavelength'])

    if only_valid:
        bands = [b for b in bands if b['valid']]
        if not bands:
            gs.fatal("No valid bands found (all marked valid=0).")

    return bands

# ---------------------------------------------------------------------------
# Endmember extraction algorithms
#
# All operate on X: (n_samples, n_bands) -- rows are pixel spectra, already
# restricted to valid (non-nodata) pixels by the caller. Each returns a list
# of `p` row indices into X identifying the extracted endmembers.
# ---------------------------------------------------------------------------


def atgp(X: np.ndarray, p: int) -> list[int]:
    """Automatic Target Generation Process (Ren & Chang, 2003).

    First endmember is the pixel with maximum L2 norm (the most "extreme"
    spectrum); each subsequent endmember is the pixel with maximum residual
    norm after projecting onto the orthogonal complement of the subspace
    spanned by the endmembers found so far.

    Uses a low-rank reformulation of the orthogonal subspace projector
    P = I - U(U^T U)^-1 U^T (U: n_bands x k, k = endmembers found so far):
    since k is always small (a handful of endmembers) while n_bands can be
    in the hundreds, computing X @ P.T directly means forming a dense
    (n_bands x n_bands) matrix and an (n_pixels x n_bands) @ (n_bands x
    n_bands) product -- forming and using only the (n_pixels x k)
    intermediate (X @ U) instead avoids that full-rank product entirely,
    which matters a lot on a plain (non-BLAS-optimized) NumPy build.
    """
    n_samples, n_bands = X.shape
    norms = np.linalg.norm(X, axis=1)
    idxs = [int(np.argmax(norms))]

    for _ in range(1, p):
        U = X[idxs].T  # (n_bands, k)
        W = np.linalg.pinv(U.T @ U)  # (k, k), symmetric
        A = X @ U  # (n_pixels, k)
        B = A @ W  # (n_pixels, k)
        projected = X - B @ U.T  # (n_pixels, n_bands)
        residual_norms = np.linalg.norm(projected, axis=1)
        residual_norms[idxs] = -1.0  # exclude already-chosen pixels
        idxs.append(int(np.argmax(residual_norms)))

    return idxs


def ppi(X: np.ndarray, p: int, n_skewers: int = 10000,
        rng: Optional[np.random.Generator] = None) -> tuple[list[int], np.ndarray]:
    """Pixel Purity Index (Boardman, 1993).

    Projects every pixel onto many random unit-vector directions ("skewers")
    in band space; a pixel's purity score is how often it lands at an
    extremum (min or max) of one of those projections. The `p` pixels with
    the highest score are returned as endmembers.

    Returns (endmember_indices, purity_scores).
    """
    rng = rng or np.random.default_rng()
    n_samples, n_bands = X.shape
    scores = np.zeros(n_samples, dtype=np.int64)

    batch = min(500, n_skewers) or 1
    done = 0
    while done < n_skewers:
        k = min(batch, n_skewers - done)
        skewers = rng.standard_normal((n_bands, k))
        skewers /= np.linalg.norm(skewers, axis=0, keepdims=True)
        # (skewers.T @ X.T) rather than (X @ skewers): both compute the same
        # values (BLAS gemm handles the transposes without copying), but the
        # result comes out as a fresh (k, n_samples) C-contiguous array, so
        # the per-skewer argmax/argmin below reduce along the fast axis.
        # Reducing along axis=0 of an (n_samples, k) array -- as the
        # mathematically-equivalent X @ skewers would require -- means
        # striding down each column, which is a well-known NumPy cache-
        # locality trap: ~40x slower here than the axis=1 reduction below.
        proj_t = skewers.T @ X.T  # (k, n_samples)
        # np.add.at is correct but famously unvectorized/slow for scatter
        # accumulation; np.bincount does the same "count occurrences" job
        # through a proper vectorized path (100x+ faster here).
        scores += np.bincount(np.argmax(proj_t, axis=1), minlength=n_samples)
        scores += np.bincount(np.argmin(proj_t, axis=1), minlength=n_samples)
        done += k

    idxs = list(np.argsort(scores)[::-1][:p])
    return [int(i) for i in idxs], scores


def _randomized_svd_components(Xc: np.ndarray, n_comp: int, n_oversamples: int = 5,
                                n_iter: int = 2,
                                rng: Optional[np.random.Generator] = None) -> np.ndarray:
    """Top n_comp right-singular-vectors of Xc via randomized SVD (Halko et
    al., 2011): only the target rank matters for cost, unlike a full SVD
    (which computes min(n_samples, n_features) components regardless of how
    many are actually needed) -- N-FINDR only ever needs p-1 components, a
    handful, out of what can be hundreds of bands.
    """
    rng = rng or np.random.default_rng()
    n_features = Xc.shape[1]
    k = min(n_comp + n_oversamples, n_features)
    Omega = rng.standard_normal((n_features, k))
    Y = Xc @ Omega
    for _ in range(n_iter):
        Y = Xc @ (Xc.T @ Y)
    Q, _ = np.linalg.qr(Y)
    B = Q.T @ Xc  # (k, n_features) -- small, cheap to SVD exactly
    _, _, Vt = np.linalg.svd(B, full_matrices=False)
    return Vt[:n_comp]


def _pca_reduce(X: np.ndarray, n_comp: int,
                 rng: Optional[np.random.Generator] = None) -> tuple[np.ndarray, np.ndarray]:
    """Reduce X: (n_samples, n_bands) to n_comp dimensions via PCA.
    Returns (Y, mean) where Y: (n_samples, n_comp)."""
    mean = X.mean(axis=0)
    Xc = X - mean
    Vt = _randomized_svd_components(Xc, n_comp, rng=rng)
    Y = Xc @ Vt.T
    return Y, mean


def nfindr(X: np.ndarray, p: int, maxit: Optional[int] = None,
           init_idxs: Optional[list[int]] = None,
           rng: Optional[np.random.Generator] = None) -> list[int]:
    """N-FINDR (Winter, 1999).

    A simplex with p vertices lives in a (p-1)-dimensional space, so X is
    first reduced via PCA to p-1 dimensions. The algorithm then repeatedly
    tries, for each endmember slot in turn, to replace it with whichever
    remaining pixel would most increase the simplex volume, using the
    standard cofactor-expansion trick: for a fixed set of the other p-1
    vertices, the simplex volume is an affine function of the candidate's
    reduced coordinates, computable for every pixel at once via a single
    matrix-vector product rather than one determinant per candidate.
    """
    rng = rng or np.random.default_rng()
    n_samples, n_bands = X.shape
    n_comp = min(p - 1, n_bands, n_samples - 1)
    if n_comp < 1:
        gs.fatal("Not enough valid pixels/bands for the requested number "
                 "of endmembers with NFINDR.")
    Y, _ = _pca_reduce(X, n_comp, rng=rng)
    # If PCA reduced to fewer than p-1 usable dimensions (e.g. more
    # endmembers requested than bands support), pad with zeros so the
    # (p x p) simplex matrix stays well-formed.
    if Y.shape[1] < p - 1:
        Y = np.hstack([Y, np.zeros((n_samples, p - 1 - Y.shape[1]))])

    if init_idxs is not None:
        idxs = list(init_idxs)
    else:
        idxs = list(int(i) for i in rng.choice(n_samples, size=p, replace=False))

    def build_M(idxs):
        return np.hstack([np.ones((p, 1)), Y[idxs]])

    if maxit is None:
        maxit = 3 * n_bands

    M = build_M(idxs)
    best_vol = abs(np.linalg.det(M))
    it = 0
    improved = True
    while improved and it < maxit:
        improved = False
        for e in range(p):
            if it >= maxit:
                break
            M_hat = np.delete(M, e, axis=0)  # (p-1, p)
            _, _, Vt = np.linalg.svd(M_hat)
            c = Vt[-1]  # null-space vector = signed cofactors for row e
            scores = c[0] + Y @ c[1:]
            scores[idxs] = 0.0
            cand = int(np.argmax(np.abs(scores)))

            trial_idxs = list(idxs)
            trial_idxs[e] = cand
            trial_M = build_M(trial_idxs)
            trial_vol = abs(np.linalg.det(trial_M))
            if trial_vol > best_vol * (1 + 1e-9):
                idxs = trial_idxs
                M = trial_M
                best_vol = trial_vol
                improved = True
            it += 1

    return idxs


def fippi(X: np.ndarray, p: int, maxit: Optional[int] = None,
          n_skewers: int = 2000,
          rng: Optional[np.random.Generator] = None) -> list[int]:
    """Fast Iterative Pixel Purity Index -- a FIPPI-inspired refinement of
    PPI (Chang & Plaza, 2006): rather than using purely random skewers
    throughout, each iteration additionally builds skewers from the
    directions between the current candidate endmembers (their spectra
    tend to lie near the true simplex edges/vertices, so scanning along
    those directions turns up purer points faster than random skewers
    alone). The candidate set converges once no skewer batch changes it.

    Note: this follows the published algorithm's core idea rather than
    reproducing it instruction-for-instruction.
    """
    rng = rng or np.random.default_rng()
    n_samples, n_bands = X.shape
    if maxit is None:
        maxit = 3 * n_bands

    # Seed with ATGP -- fast, deterministic, and a reasonable starting guess.
    idxs = atgp(X, p)

    for _ in range(maxit):
        # Skewers: directions between all pairs of current endmembers, plus
        # a modest batch of random ones to keep exploring.
        E = X[idxs]  # (p, n_bands)
        pair_dirs = []
        for i in range(p):
            for j in range(i + 1, p):
                d = E[i] - E[j]
                norm = np.linalg.norm(d)
                if norm > 1e-12:
                    pair_dirs.append(d / norm)
        skewers = np.array(pair_dirs).T if pair_dirs else np.empty((n_bands, 0))
        if n_skewers > 0:
            rand_skewers = rng.standard_normal((n_bands, n_skewers))
            rand_skewers /= np.linalg.norm(rand_skewers, axis=0, keepdims=True)
            skewers = np.hstack([skewers, rand_skewers]) if skewers.size else rand_skewers

        # See ppi()'s comment: reduce along the fast (contiguous) axis by
        # computing the transposed projection directly, rather than
        # argmax/argmin along axis=0 of an (n_samples, k) array.
        proj_t = skewers.T @ X.T
        extremal = set(np.argmax(proj_t, axis=1).tolist()) | set(np.argmin(proj_t, axis=1).tolist())
        extremal |= set(idxs)

        candidates = sorted(extremal)
        Xc = X[candidates]
        # Re-run ATGP restricted to the extremal candidate set to pick the p
        # most mutually-distinct spectra among them.
        new_local_idxs = atgp(Xc, p)
        new_idxs = [candidates[i] for i in new_local_idxs]

        if sorted(new_idxs) == sorted(idxs):
            break
        idxs = new_idxs

    return idxs

# ---------------------------------------------------------------------------
# Spectral unmixing (abundance mapping)
#
# All operate per-pixel: X: (n_samples, n_bands), E: (p, n_bands) endmember
# spectra. Returns A: (n_samples, p) abundances.
# ---------------------------------------------------------------------------


def unmix_ucls(X: np.ndarray, E: np.ndarray) -> np.ndarray:
    """Unconstrained least squares: A = X @ pinv(E)."""
    return X @ np.linalg.pinv(E)


def unmix_nnls(X: np.ndarray, E: np.ndarray) -> np.ndarray:
    """Non-negativity-constrained least squares (per pixel)."""
    from scipy.optimize import nnls
    n_samples = X.shape[0]
    p = E.shape[0]
    A = np.empty((n_samples, p), dtype=np.float64)
    Et = E.T  # (n_bands, p)
    for i in range(n_samples):
        A[i], _ = nnls(Et, X[i])
    return A


def unmix_fcls(X: np.ndarray, E: np.ndarray, delta: float = 1e4) -> np.ndarray:
    """Fully constrained least squares (non-negative + sum-to-one), via the
    standard trick of augmenting the system with a large-weight row enforcing
    sum-to-one and solving as NNLS (Heinz & Chang, 2001) -- avoids needing a
    general QP solver (e.g. cvxopt) for an exact-constraint result.
    """
    from scipy.optimize import nnls
    n_samples, n_bands = X.shape
    p = E.shape[0]
    E_aug = np.vstack([E.T, delta * np.ones((1, p))])  # (n_bands+1, p)
    A = np.empty((n_samples, p), dtype=np.float64)
    for i in range(n_samples):
        x_aug = np.concatenate([X[i], [delta]])
        A[i], _ = nnls(E_aug, x_aug)
    return A

# ---------------------------------------------------------------------------
# Column naming / CSV / vector helpers
# ---------------------------------------------------------------------------


def _wl_field_name(wavelength_nm: float, unit: str) -> str:
    value = wavelength_nm if unit == 'nm' else wavelength_nm / 1000.0
    s = f"{value:.4f}".rstrip('0').rstrip('.')
    s = s.replace('.', '_').replace('-', 'neg_')
    return f"wl_{s}"


def _dedupe_names(names: list[str]) -> list[str]:
    seen: dict[str, int] = {}
    out = []
    for n in names:
        if n not in seen:
            seen[n] = 0
            out.append(n)
        else:
            seen[n] += 1
            out.append(f"{n}_{seen[n]}")
    return out


def _reproject_to_lonlat(xy_pairs: list[tuple[float, float]]) -> list[tuple[float, float]]:
    """Reproject a list of (x, y) native-CRS coordinates to (lon, lat) WGS84
    via m.proj (cs2cs frontend) -- works for any source projection, not just
    the current location's."""
    input_str = "\n".join(f"{x} {y}" for x, y in xy_pairs)
    proc = gs.start_command('m.proj', flags='od', input='-', separator='space',
                            stdin=gs.PIPE, stdout=gs.PIPE, stderr=gs.PIPE)
    stdout, stderr = proc.communicate(input=input_str)
    if proc.returncode != 0:
        gs.fatal(f"m.proj failed: {stderr}")
    out = []
    for line in stdout.strip().split('\n'):
        parts = line.split()
        out.append((float(parts[0]), float(parts[1])))
    return out


_LOWER_IS_BETTER = {'sam': True, 'euclidean': True, 'correlation': False}


def identify_endmembers(E: np.ndarray, field_names: list[str], *, library: str,
                        source_databases: list[str], dataset_ids: list[str],
                        similarity_method: str, min_overlap_bands: int,
                        min_overlap_fraction: float, top_n: int,
                        include_spectra: bool = False) -> list[Optional[dict]]:
    """Identify each extracted endmember against the shared i.hyper.lib_*
    spectral library by calling i.hyper.speclookup directly (as a real
    GRASS module invocation, not a reimplementation of its matching logic)
    -- one call handles every endmember at once, since i.hyper.speclookup
    already ranks one result set per query_csv row.

    Returns one dict per endmember (None if no library candidate matched
    at all), each with the best match's identity/metadata, its similarity
    score, and a confidence margin to the runner-up (positive means the
    top match is clearly better than the second-best, in whichever
    direction similarity_method treats as "better"; None if top_n was too
    low to have a runner-up, or none was found). include_spectra also asks
    i.hyper.speclookup (-s) for the matched record's own wavelengths/
    values -- needed to overplot it against the extracted endmember, not
    otherwise carried in the per-row CSV/JSON output."""
    n = E.shape[0]
    tmp_csv = gs.tempfile()
    tmp_json = gs.tempfile()
    with open(tmp_csv, 'w', newline='') as f:
        writer = csv_module.writer(f)
        writer.writerow(['x', 'y'] + field_names)
        for i in range(n):
            writer.writerow([0, 0] + [f"{v:.6f}" for v in E[i]])

    kwargs = dict(
        query_csv=tmp_csv, output=tmp_json, output_format='json',
        top_n=max(top_n, 2), similarity_method=similarity_method,
        min_overlap_bands=min_overlap_bands, min_overlap_fraction=min_overlap_fraction,
        quiet=True, overwrite=True,
    )
    if include_spectra:
        kwargs['flags'] = 's'
    if library:
        kwargs['library'] = library
    if source_databases:
        kwargs['source_database'] = source_databases
    if dataset_ids:
        kwargs['dataset_id'] = dataset_ids

    gs.message("Identifying endmembers against the shared spectral library (i.hyper.speclookup)…")
    try:
        gs.run_command('i.hyper.speclookup', **kwargs)
        with open(tmp_json) as f:
            matches = json_module.load(f) if os.path.getsize(tmp_json) else []
    except Exception as exc:
        gs.warning(f"Identification via i.hyper.speclookup failed, skipping: {exc}")
        matches = []
    finally:
        for p in (tmp_csv, tmp_json):
            if os.path.exists(p):
                os.unlink(p)

    by_query: dict[str, list[dict]] = {}
    for m in matches:
        by_query.setdefault(m['query'], []).append(m)
    for lst in by_query.values():
        lst.sort(key=lambda m: m['rank'])

    lower_better = _LOWER_IS_BETTER.get(similarity_method, True)
    results: list[Optional[dict]] = []
    for i in range(n):
        ranked = by_query.get(f"row{i + 1}", [])
        if not ranked:
            results.append(None)
            continue
        top = ranked[0]
        margin = None
        if len(ranked) > 1:
            second = ranked[1]
            margin = (second['score'] - top['score']) if lower_better else (top['score'] - second['score'])
        results.append({
            'match_source': top.get('source_database'),
            'match_dataset': top.get('dataset_id'),
            'match_record': top.get('record_id'),
            'match_title': top.get('dataset_title'),
            'match_organization': top.get('organization'),
            'match_method': similarity_method,
            'match_score': top.get('score'),
            'match_overlap_bands': top.get('n_overlap_bands'),
            'match_margin': margin,
            'match_extra_metadata': top.get('extra_metadata'),
            'match_wavelengths': top.get('wavelengths'),
            'match_values': top.get('values'),
        })
    return results


def _default_plot_dir() -> str:
    """The current GRASS location's own directory (e.g.
    $GISDBASE/$LOCATION_NAME/) -- a sensible default regardless of which
    project a user runs this in, since a plot documenting a scene's
    endmembers belongs alongside that scene's own data."""
    genv = gs.gisenv()
    return os.path.join(genv['GISDBASE'], genv['LOCATION_NAME'])


def _annotate_endpoint(ax, x, y, number, color):
    """A small bold number at each curve's right end -- lets every
    endmember/reference be identified at a glance without hunting through
    a many-entry legend."""
    ax.annotate(str(number), (x, y), color=color, fontsize=9, fontweight='bold',
                xytext=(4, 0), textcoords='offset points', va='center')


def plot_endmembers(wavelengths: np.ndarray, wavelength_unit: str, E: np.ndarray,
                    matches: list[Optional[dict]], input_map: str, extraction_method: str,
                    plot_path_endmembers: str, plot_path_reference: str, interactive: bool) -> None:
    """Two separate, single-purpose plots rather than one crowded overlay:

    1. Every extracted endmember's own spectrum together, numbered --
       lets you compare the endmembers' shapes against each other.
    2. Every identified library match's own spectrum together, numbered
       to match (1), each labeled with its full identity (title, record
       ID, source, similarity score) -- lets you compare the reference
       materials against each other, and cross-reference which endmember
       each belongs to via the shared number/color. Only written if -i
       found at least one match; a numeric score alone, without seeing
       the reference spectrum's own shape, is not enough to trust an
       identification.
    """
    import matplotlib
    if not interactive:
        matplotlib.use('Agg')
    import matplotlib.pyplot as plt

    n = E.shape[0]
    wl_min, wl_max = float(np.min(wavelengths)), float(np.max(wavelengths))
    cmap = plt.get_cmap('tab10' if n <= 10 else 'tab20')
    colors = [cmap(i % cmap.N) for i in range(n)]

    # --- Graph 1: extracted endmember spectra ---------------------------
    fig1, ax1 = plt.subplots(figsize=(10, 6))
    for i in range(n):
        ax1.plot(wavelengths, E[i], color=colors[i], linewidth=1.6, label=str(i + 1))
        _annotate_endpoint(ax1, wavelengths[-1], E[i][-1], i + 1, colors[i])
    ax1.set_xlabel(f"Wavelength ({wavelength_unit})")
    ax1.set_ylabel("Reflectance")
    ax1.set_xlim(wl_min, wl_max)
    ax1.set_ylim(0.0, 1.0)  # physical reflectance range; any excursion in the
    # underlying data (e.g. a water-vapor-band retrieval artifact) is a
    # known data-quality issue, not something the plot should rescale for
    ax1.set_title(f"Extracted endmembers ({extraction_method}) — {input_map}")
    ax1.legend(title="Endmember", fontsize=8, ncol=2 if n > 6 else 1, loc='best')
    fig1.tight_layout()
    os.makedirs(os.path.dirname(plot_path_endmembers) or '.', exist_ok=True)
    fig1.savefig(plot_path_endmembers, dpi=150)
    gs.message(f"Wrote endmember spectra plot → {plot_path_endmembers}")
    if interactive:
        plt.show()
    plt.close(fig1)

    # --- Graph 2: identified reference spectra, one per endmember -------
    has_spectrum = [
        m is not None and m.get('match_wavelengths') and m.get('match_values')
        for m in matches
    ]
    if not any(has_spectrum):
        gs.verbose("No identified library matches with spectra to plot "
                  "(run with -i to identify endmembers first).")
        return

    fig2, ax2 = plt.subplots(figsize=(11, 6))
    for i in range(n):
        if not has_spectrum[i]:
            continue
        m = matches[i]
        # A matched reference spectrum (e.g. a Nicolet FTIR record
        # extending to 200,000+ nm) can natively cover a far wider range
        # than the endmember itself -- clip to the endmember's own range
        # (not just an xlim visual crop) so the reference's out-of-range
        # values don't also distort the y-axis scale via autoscaling.
        mwl = np.asarray(m['match_wavelengths'], dtype=float)
        mval = np.asarray(m['match_values'], dtype=float)
        in_range = (mwl >= wl_min) & (mwl <= wl_max)
        if not in_range.any():
            continue
        mwl, mval = mwl[in_range], mval[in_range]
        label = (f"{i + 1}: {m['match_title']} ({m['match_record']}, {m['match_source']}) "
                 f"[{m['match_method']}={m['match_score']:.4g}, "
                 f"{m['match_overlap_bands']} bands]")
        ax2.plot(mwl, mval, color=colors[i], linewidth=1.4, label=label)
        _annotate_endpoint(ax2, mwl[-1], mval[-1], i + 1, colors[i])

    ax2.set_xlabel(f"Wavelength ({wavelength_unit})")
    ax2.set_ylabel("Reflectance")
    ax2.set_xlim(wl_min, wl_max)
    ax2.set_ylim(0.0, 1.0)
    ax2.set_title(f"Identified reference spectra by endmember number — {input_map}")
    ax2.legend(title="Endmember: reference match", fontsize=7.5, loc='best')
    fig2.tight_layout()
    os.makedirs(os.path.dirname(plot_path_reference) or '.', exist_ok=True)
    fig2.savefig(plot_path_reference, dpi=150)
    gs.message(f"Wrote reference spectra plot → {plot_path_reference}")
    if interactive:
        plt.show()
    plt.close(fig2)

# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------


def main(options, flags):
    input_map = options['input']
    output_vector = options.get('output', '')
    output_file = options.get('output_file', '')
    output_format = options.get('output_format', 'csv') or 'csv'
    abundance_prefix = options.get('abundance_prefix', '')
    n_endmembers = int(options['n_endmembers'])
    extraction_method = options.get('extraction_method', 'NFINDR') or 'NFINDR'
    unmixing_method = options.get('unmixing_method', 'FCLS') or 'FCLS'
    maxit = int(options['maxit']) if options.get('maxit') else None
    ppi_skewers = int(options.get('ppi_skewers', '10000') or '10000')
    random_seed = int(options['random_seed']) if options.get('random_seed') else None
    min_wl = float(options['min_wavelength']) if options.get('min_wavelength') else None
    max_wl = float(options['max_wavelength']) if options.get('max_wavelength') else None
    wavelength_unit = options.get('wavelength_unit', 'nm') or 'nm'
    atgp_init = not flags['n']
    only_valid = flags['b']
    use_lonlat = flags['l']
    identify = flags['i']
    spec_library = options.get('spec_library', '')
    spec_source_databases = [s for s in (options.get('spec_source_database', '') or '').split(',') if s]
    spec_dataset_ids = [s for s in (options.get('spec_dataset_id', '') or '').split(',') if s]
    spec_similarity_method = options.get('spec_similarity_method', 'sam') or 'sam'
    spec_min_overlap_bands = int(options.get('spec_min_overlap_bands', '5') or '5')
    spec_min_overlap_fraction = float(options.get('spec_min_overlap_fraction', '0.55') or '0.55')
    spec_top_n = int(options.get('spec_top_n', '3') or '3')
    make_plot = flags['p']
    plot_interactive = flags['w']
    plot_dir = options.get('plot_dir', '') or _default_plot_dir()

    if not (output_vector or output_file or make_plot):
        gs.fatal("At least one of output, output_file, or -p is required.")

    if n_endmembers < 2:
        gs.fatal("n_endmembers must be >= 2")

    rng = np.random.default_rng(random_seed)

    # --- Band metadata -------------------------------------------------
    bands = get_band_info(input_map, only_valid=only_valid)
    if min_wl is not None:
        bands = [b for b in bands if b['wavelength'] >= min_wl]
    if max_wl is not None:
        bands = [b for b in bands if b['wavelength'] <= max_wl]
    if not bands:
        gs.fatal("No bands left after min_wavelength/max_wavelength filtering.")
    wavelengths = np.array([b['wavelength'] for b in bands], dtype=np.float64)
    Z = len(bands)

    if n_endmembers > Z + 1 and extraction_method != 'PPI':
        gs.fatal(f"Only PPI can extract more endmembers ({n_endmembers}) "
                f"than there are bands ({Z}).")

    # --- Region: preserve the caller's horizontal extent/resolution, only
    # align the 3D depth window to the raster's own native depth stack.
    # (`g.region raster3d=<map>` resets BOTH 2D and 3D to the raster's full
    # native footprint, silently discarding any smaller area the caller had
    # selected -- see i.hyper.spectroscopy's notes on this exact bug.)
    depth_info = gs.parse_command('r3.info', map=input_map, flags='g')
    region = gs.region()
    gs.run_command('g.region',
                   nsres3=region['nsres'], ewres3=region['ewres'],
                   b=depth_info['bottom'], t=depth_info['top'],
                   tbres=depth_info['tbres'])
    nrows = int(region['rows'])
    ncols = int(region['cols'])
    n_pixels = nrows * ncols

    mem_gb = Z * n_pixels * 4 / 1e9
    if mem_gb > 2:
        gs.warning(f"Loading the full cube needs ~{mem_gb:.1f} GB of memory "
                  f"({Z} bands x {nrows}x{ncols} pixels). Endmember "
                  "extraction needs the whole scene at once (unlike "
                  "per-pixel classification), so this cannot be chunked -- "
                  "consider restricting the region to a smaller area of "
                  "interest first.")

    # --- Extract bands and load the full cube ---------------------------
    gs.message(f"Extracting {Z} bands ({nrows}x{ncols} pixels)…")
    tmp_names = []
    for z_idx, b in enumerate(bands):
        gs.percent(z_idx, Z, 2)
        tmp_names.append(extract_band(input_map, b['band']))
    gs.percent(Z, Z, 2)

    from grass.pygrass.raster import RasterRow
    cube = np.empty((Z, n_pixels), dtype=np.float32)
    handles = [RasterRow(name) for name in tmp_names]
    try:
        for h in handles:
            h.open()
        for z_idx, h in enumerate(handles):
            gs.percent(z_idx, Z, 2)
            for r in range(nrows):
                row_arr = np.array(h[r], dtype=np.float32)
                cube[z_idx, r * ncols:(r + 1) * ncols] = row_arr
        gs.percent(Z, Z, 2)
    finally:
        for h in handles:
            h.close()

    nodata_mask = np.all(np.isnan(cube), axis=0)
    valid_flat_idx = np.where(~nodata_mask)[0]
    if valid_flat_idx.size < n_endmembers:
        gs.fatal("Fewer valid (non-nodata) pixels than requested endmembers.")

    X = cube[:, valid_flat_idx].T  # (n_valid, Z)
    del cube

    # --- Endmember extraction --------------------------------------------
    if extraction_method in ('PPI', 'FIPPI'):
        gs.verbose(
            "PPI/FIPPI runtime scales with ppi_skewers and the number of "
            "valid pixels -- lower ppi_skewers for a quicker, less "
            "statistically robust estimate."
        )
    gs.message(f"Extracting {n_endmembers} endmembers using {extraction_method}…")
    if extraction_method == 'ATGP':
        local_idxs = atgp(X, n_endmembers)
    elif extraction_method == 'PPI':
        local_idxs, _scores = ppi(X, n_endmembers, n_skewers=ppi_skewers, rng=rng)
    elif extraction_method == 'NFINDR':
        init_idxs = atgp(X, n_endmembers) if atgp_init else None
        local_idxs = nfindr(X, n_endmembers, maxit=maxit, init_idxs=init_idxs, rng=rng)
    elif extraction_method == 'FIPPI':
        local_idxs = fippi(X, n_endmembers, maxit=maxit,
                           n_skewers=max(1, ppi_skewers // 5), rng=rng)
    else:
        gs.fatal(f"Unknown extraction_method: {extraction_method}")

    E = X[local_idxs]  # (p, Z) endmember spectra
    flat_idx = valid_flat_idx[local_idxs]
    rows = flat_idx // ncols
    cols = flat_idx % ncols
    xs = region['w'] + (cols + 0.5) * region['ewres']
    ys = region['n'] - (rows + 0.5) * region['nsres']

    # --- Vector output -----------------------------------------------------
    field_names = _dedupe_names([_wl_field_name(wl, wavelength_unit) for wl in wavelengths])

    matches: list[Optional[dict]] = [None] * n_endmembers
    if identify:
        matches = identify_endmembers(
            E, field_names, library=spec_library, source_databases=spec_source_databases,
            dataset_ids=spec_dataset_ids, similarity_method=spec_similarity_method,
            min_overlap_bands=spec_min_overlap_bands,
            min_overlap_fraction=spec_min_overlap_fraction, top_n=spec_top_n,
            include_spectra=make_plot,
        )
        n_identified = sum(1 for m in matches if m is not None)
        gs.message(f"Identified {n_identified} of {n_endmembers} endmember(s) "
                  f"(method={spec_similarity_method}).")
        for i, m in enumerate(matches):
            if m is None:
                gs.verbose(f"Endmember {i + 1}: no library match found.")
                continue
            margin_txt = f", margin={m['match_margin']:.4g}" if m['match_margin'] is not None else ""
            gs.message(
                f"Endmember {i + 1}: {m['match_title']} ({m['match_record']}, "
                f"{m['match_source']}) -- {m['match_method']}={m['match_score']:.6g}"
                f"{margin_txt} ({m['match_overlap_bands']} overlapping bands)"
            )

    if make_plot:
        plot_base = output_vector or input_map
        # Avoid a redundant "..._endmembers_endmembers.png" when the base
        # name (typically the user's own chosen output= vector name)
        # already contains "endmember". Both filenames are always
        # generated by the module itself -- there is no user-facing
        # option to name them individually, only plot_dir to choose where
        # they land.
        suffix = "" if "endmember" in plot_base.lower() else "_endmembers"
        plot_path_endmembers = os.path.join(plot_dir, f"{plot_base}{suffix}_spectra.png")
        plot_path_reference = os.path.join(plot_dir, f"{plot_base}{suffix}_reference_spectra.png")
        plot_endmembers(wavelengths, wavelength_unit, E, matches, input_map,
                        extraction_method, plot_path_endmembers, plot_path_reference,
                        plot_interactive)

    # match_* text fields can contain the same '|' character v.in.ascii uses
    # as its field separator here -- sanitize defensively so a stray pipe in
    # a harvested title/organization string can't corrupt column alignment.
    def _pipe_safe(s):
        return "" if s is None else str(s).replace("|", "/")

    if output_vector:
        gs.message(f"Writing endmember vector map → {output_vector}…")
        ascii_tmp = gs.tempfile()
        with open(ascii_tmp, 'w') as f:
            for i in range(n_endmembers):
                row = [f"{xs[i]:.10f}", f"{ys[i]:.10f}"] + [f"{v:.6f}" for v in E[i]]
                if identify:
                    m = matches[i] or {}
                    row += [
                        _pipe_safe(m.get('match_source')), _pipe_safe(m.get('match_dataset')),
                        _pipe_safe(m.get('match_record')), _pipe_safe(m.get('match_title')),
                        _pipe_safe(m.get('match_organization')),
                        "" if m.get('match_score') is None else f"{m['match_score']:.6f}",
                        "" if m.get('match_overlap_bands') is None else str(m['match_overlap_bands']),
                        "" if m.get('match_margin') is None else f"{m['match_margin']:.6f}",
                    ]
                f.write('|'.join(row) + '\n')

        columns = "x double precision, y double precision, " + \
            ", ".join(f"{name} double precision" for name in field_names)
        if identify:
            columns += (
                ", match_source varchar(64), match_dataset varchar(255), "
                "match_record varchar(255), match_title varchar(255), "
                "match_organization varchar(255), match_score double precision, "
                "match_overlap_bands int, match_margin double precision"
            )
        gs.run_command('v.in.ascii', input=ascii_tmp, output=output_vector,
                       format='point', separator='pipe', x=1, y=2, cat=0,
                       columns=columns, overwrite=True, quiet=True)
        os.unlink(ascii_tmp)

    # --- CSV/JSON output -----------------------------------------------
    if output_file:
        gs.message(f"Writing endmember spectra ({output_format}) → {output_file}…")
        if use_lonlat:
            coord_pairs = _reproject_to_lonlat(list(zip(xs.tolist(), ys.tolist())))
            coord_names = ('lon', 'lat')
        else:
            coord_pairs = list(zip(xs.tolist(), ys.tolist()))
            coord_names = ('x', 'y')

        match_field_names = [
            'match_source', 'match_dataset', 'match_record', 'match_title',
            'match_organization', 'match_method', 'match_score',
            'match_overlap_bands', 'match_margin', 'match_extra_metadata',
        ]

        if output_format == 'json':
            records = []
            for i in range(n_endmembers):
                rec = {coord_names[0]: coord_pairs[i][0],
                       coord_names[1]: coord_pairs[i][1]}
                for name, val in zip(field_names, E[i]):
                    rec[name] = float(val)
                if identify:
                    m = matches[i] or {}
                    for name in match_field_names:
                        rec[name] = m.get(name)
                records.append(rec)
            with open(output_file, 'w') as f:
                json_module.dump(records, f, indent=2)
        else:
            with open(output_file, 'w', newline='') as f:
                writer = csv_module.writer(f)
                header = list(coord_names) + field_names
                if identify:
                    header += match_field_names
                writer.writerow(header)
                for i in range(n_endmembers):
                    row = [coord_pairs[i][0], coord_pairs[i][1]] + [float(v) for v in E[i]]
                    if identify:
                        m = matches[i] or {}
                        row += [m.get(name) for name in match_field_names]
                    writer.writerow(row)

    # --- Optional abundance mapping (spectral unmixing) -------------------
    if abundance_prefix:
        gs.message(f"Unmixing abundances using {unmixing_method}…")
        if unmixing_method == 'UCLS':
            A_valid = unmix_ucls(X, E)
        elif unmixing_method == 'NNLS':
            A_valid = unmix_nnls(X, E)
        elif unmixing_method == 'FCLS':
            A_valid = unmix_fcls(X, E)
        else:
            gs.fatal(f"Unknown unmixing_method: {unmixing_method}")

        reg = gs.region()
        ascii_header = (
            f"north: {reg['n']}\nsouth: {reg['s']}\n"
            f"east: {reg['e']}\nwest: {reg['w']}\n"
            f"rows: {nrows}\ncols: {ncols}\n"
        )
        for e_idx in range(n_endmembers):
            full = np.full(n_pixels, np.nan, dtype=np.float32)
            full[valid_flat_idx] = A_valid[:, e_idx]
            rastname = f"{abundance_prefix}_{e_idx + 1}"
            ascii_tmp = gs.tempfile()
            with open(ascii_tmp, 'w') as f:
                f.write(ascii_header)
                np.savetxt(f, full.reshape(nrows, ncols), fmt='%.6f')
            gs.run_command('r.in.ascii', input=ascii_tmp, output=rastname,
                           null_value='nan', overwrite=True, quiet=True)
            os.unlink(ascii_tmp)
            gs.run_command('r.colors', map=rastname, color='viridis', quiet=True)

    gs.message(f"Done: {n_endmembers} endmember(s) extracted with {extraction_method}.")


if __name__ == "__main__":
    options, flags = gs.parser()
    sys.exit(main(options, flags))
