import glob
import healpy as hp
import numpy as np
import matplotlib.pyplot as plt

import ReadMC as rmc
import AnalysisMC as amc

import qubic
from qubic import equ2gal

stokes = ['I', 'Q', 'U']

# ================= Get the simulation files ================
# repository where the .fits was saved
date = '20190704'
# rep_simu = './TEST/{}/'.format(date)
rep_simu = '/home/louisemousset/QUBIC/Qubic_work/SpectroImagerie/SimuLouise/Noise_MCMC_201907/' + date + '/'

# Simulation name
name = 'try50reals'

# Dictionary saved during the simulation
d = qubic.qubicdict.qubicDict()
d.read_from_file(rep_simu + date + '_' + name + '.dict')

# Coordinates of the zone observed in the sky
center = equ2gal(d['RA_center'], d['DEC_center'])

# Get fits files names in a list
fits_noise = np.sort(glob.glob(rep_simu + date + '_' + name + '*noiselessFalse*.fits'))
fits_noiseless = glob.glob(rep_simu + date + '_' + name + '*noiselessTrue*.fits')

#Number of noise realisations
nreals = len(fits_noise)
print('nreals = ', nreals)

# Number of subbands used during the simulation
nf_recon = d['nf_recon'][0]
print('nf_recon = ', nf_recon)


# ================= Get maps ================
# Get seen map (observed pixels)
seen_map = rmc.get_seenmap(fits_noise[0])

# Number of pixels and nside
npix = len(seen_map)
ns = d['nside']

# Get one full maps
real = 10
if real >= nreals:
    raise ValueError('Invalid index of realization')
maps_recon, maps_convo, maps_diff = rmc.get_maps(fits_noise[real])
print('Getting maps with shape : {}'.format(maps_recon.shape))

# Look at the maps
isub = 0
if isub >= nf_recon:
    raise ValueError('Invalid index of subband')

plt.figure('Noise maps real{}'.format(real))
for i in xrange(3):
    hp.gnomview(maps_convo[isub, :, i], rot=center, reso=9, sub=(3, 3, i + 1),
                title='conv ' + stokes[i] + ' subband {}/{}'.format(isub+1, nf_recon))
    hp.gnomview(maps_recon[isub, :, i], rot=center, reso=9, sub=(3, 3, 3 + i + 1),
                title='recon ' + stokes[i] + ' subband {}/{}'.format(isub+1, nf_recon))
    hp.gnomview(maps_diff[isub, :, i], rot=center, reso=9, sub=(3, 3, 6 + i + 1),
                title='diff ' + stokes[i] + ' subband {}/{}'.format(isub+1, nf_recon))

# Get one patch
maps_recon_cut, maps_convo_cut, maps_diff_cut = rmc.get_patch(fits_noise[0], seen_map)
print('Getting patches with shape : {}'.format(maps_recon_cut.shape))

npix_patch = np.shape(maps_recon_cut)[1]
# Get all patches (all noise realisations)
all_fits, all_patch_recon, all_patch_conv, all_patch_diff = rmc.get_patch_many_files(
    rep_simu, date + '_' + name + '*noiselessFalse*.fits')
print('Getting all patch realizations with shape : {}'.format(all_patch_recon.shape))

# ================== Look at residuals ===============
residuals = all_patch_recon - np.mean(all_patch_recon, axis=0)

# Histogram of the residuals (first real, first subband)
isub = 2
if isub >= nf_recon:
    raise ValueError('Invalid index of subband')

real = 0
if real >= nreals:
    raise ValueError('Invalid index of realization')

plt.figure('Residuals isub{} real{}'.format(isub, real))
for i in xrange(3):
    plt.subplot(1, 3, i + 1)
    data = np.ravel(residuals[real, isub, :, i])
    std = np.std(data)
    mean = np.mean(data)
    plt.hist(data, range=[-20, 20], bins=100, label='std={0:.2f} mean={0:.2f}'.format(std, mean))
    plt.title(stokes[i] + ' real{0} subband{1}/{2}'.format(real, isub+1, nf_recon))
    plt.legend()

# ================= Correlations matrices =======================
# Correlation between pixels
cov_pix, corr_pix = amc.get_covcorr_between_pix(residuals, verbose=True)

isub = 1
if isub >= nf_recon:
    raise ValueError('Invalid index of subband')

plt.figure('Cov corr pix isub{}'.format(isub))

for istk in range(3):
    plt.subplot(2,3,istk+1)
    plt.title('Cov matrix pix, {}, subband{}/{}'.format(stokes[istk], isub+1, nf_recon))
    plt.imshow(cov_pix[isub, istk, :, :], vmin=-50, vmax=50)
    plt.colorbar()

    plt.subplot(2, 3, istk+4)
    plt.title('Corr matrix pix, {}, subband{}/{}'.format(stokes[istk], isub+1, nf_recon))
    plt.imshow(corr_pix[isub, istk, :, :], vmin=-0.6, vmax=0.6)
    plt.colorbar()

# Compute distances associated to the correlation matrix
distance = np.empty((nf_recon, 3))
for isub in range(nf_recon):
    for istk in range(3):
        distance[isub, istk] = amc.distance_square(corr_pix[isub, istk, :, :])

# Correlations between subbands and I, Q, U
amc.get_covcorr_patch(residuals, doplot=True, bins=60)

# ================= Make zones ============
nzones = 4
residuals_zones = np.empty((nreals, nzones, nf_recon, npix_patch, 3))
for real in range(nreals):
    if real == 0:
        pix_per_zone, residuals_zones[real,...] = rmc.make_zones(residuals[real,...], nzones, ns, center, seen_map)

    else:
        _, residuals_zones[real,...] = rmc.make_zones(residuals[real,...], nzones, ns, center, seen_map,
                                  verbose=False, doplot=False)

# ================= Statistical study over the zones ============
# Correlation between pixels
all_zones = []
print('all_zones is a list, each element is one zone and has a shape :'
      '\n(nreals, nf_sub_rec, npix_per_zone, 3)')
all_cov = []
all_corr = []
for izone in range(nzones):

    # remove pixel outside the zone
    zone = residuals_zones[:, izone, ...]
    indices = np.unique(np.nonzero(zone)[2])
    all_zones.append(np.take(zone, indices, axis=2))

    # Correlation between pixels
    cov_pix, corr_pix = amc.get_covcorr_between_pix(all_zones[izone], verbose=True)
    all_cov.append(cov_pix)
    all_corr.append(corr_pix)

isub = 0
if isub >= nf_recon:
    raise ValueError('Invalid index of subband')

plt.figure('Cov corr pix isub{} {}zones'.format(isub, nzones))
for izone in range(nzones):
    for istk in range(3):
        plt.subplot(4, 6, 6*izone+istk+1)
        plt.title('{}, band{}/{}, zone{}/{}'.format(stokes[istk], isub+1, nf_recon, izone+1, nzones))
        plt.imshow(all_cov[izone][isub, istk, :, :], vmin=-50, vmax=50)
        plt.colorbar()

        plt.subplot(4, 6, 6*izone+istk+4)
        plt.title('{}, band{}/{}, zone{}/{}'.format(stokes[istk], isub+1, nf_recon, izone+1, nzones))
        plt.imshow(all_corr[izone][isub, istk, :, :], vmin=-0.6, vmax=0.6)
        plt.colorbar()



# ================= Noise Evolution as a function of the subband number=======================
# This part should be rewritten (old)
# To do that, you need many realisations and different nfsub_rec

allmeanmat = amc.get_rms_covar(nsubvals, seenmap_recon, allmaps_recon)[1]
rmsmap_cov = amc.get_rms_covarmean(nsubvals, seenmap_recon, allmaps_recon, allmeanmat)[1]
mean_rms_cov = np.sqrt(np.mean(rmsmap_cov ** 2, axis=2))

plt.plot(nsubvals, np.sqrt(nsubvals), 'k', label='Optimal $\sqrt{N}$', lw=2)
for i in xrange(3):
    plt.plot(nsubvals, mean_rms_cov[:, i] / mean_rms_cov[0, i] * np.sqrt(nsubvals), label=stokes[i], lw=2, ls='--')
plt.xlabel('Number of sub-frequencies')
plt.ylabel('Relative maps RMS')
plt.legend()
