from __future__ import division, print_function
import os
import qubic
from qubicpack.utilities import Qubic_DataDir
import healpy as hp
import numpy as np
import matplotlib as mpl
import matplotlib.pyplot as plt
import sys


def select_det(q, id, multiband=True):
    id = [id]
    if multiband:
        for i in range(q.nsubbands ):
            detector_i = q[i].detector[id]
            q[i].detector = detector_i
    else:
        detector_i = q.detector[id]
        q.detector = detector_i
    return


stokes = ['I', 'Q', 'U']

mpl.style.use('classic')
name = 'test_scan_source'
resultDir = '%s' % name
os.makedirs(resultDir, exist_ok=True)

alaImager = True        # if True, the beam will be a simple gaussian
component = 1           # Choose the component number to plot (IQU)
oneComponent = False    # True if you want to study only I component, otherwise False if you study IQU
sel_det = True          # True if you want to use one detector, False if you want to use all detectors in focal plane
id_det = 4              # if sel_det == True, choose detector number
multiband = True        # True if you want to use a multiband instrument and make TOD with a MultibandAcquisition

# Dictionnary
global_dir = Qubic_DataDir(datafile='instrument.py', datadir=os.environ['QUBIC_DATADIR'])
print('global_dir: ', global_dir)
d = qubic.qubicdict.qubicDict()
d.read_from_file(global_dir + '/dicts/global_source_oneDet.dict')

# Scene
s = qubic.QubicScene(d)

# Instrument
if multiband:
    q = qubic.QubicMultibandInstrument(d)
else:
    q = qubic.QubicInstrument(d)
if sel_det:
    select_det(q, id_det, multiband=multiband)

# Pointing
p = qubic.get_pointing(d)

fix_azimuth = d['fix_azimuth']
print('fix_azimuth', fix_azimuth)

plt.figure(figsize=(12, 8))
plt.subplot(411)
plt.plot(p.time, p.azimuth, 'bo')
plt.ylabel('Azimuth')
plt.subplot(412)
plt.plot(p.time, p.elevation, 'bo')
plt.ylabel('Elevation')
plt.subplot(413)
plt.plot(p.time, p.pitch, 'bo')
plt.ylabel('pitch angle')
plt.subplot(414)
plt.plot(p.time, p.angle_hwp, 'bo')
plt.ylabel('HWP angle')
plt.savefig(resultDir+'/%s_pointing.png'%name, bbox_inches='tight')

# Make a point source
m0 = np.zeros(12 * d['nside'] ** 2)
x0 = np.zeros((d['nf_sub'], len(m0), 3))
id = hp.pixelfunc.ang2pix(d['nside'], fix_azimuth['el'], fix_azimuth['az'],
                          lonlat=True)
source = m0 * 0
source[id] = 1
arcToRad = np.pi / (180 * 60.)
source = hp.sphtfunc.smoothing(source, fwhm=30 * arcToRad)
x0[:, :, component] = source
hp.mollview(x0[0, :, component])
plt.show()

if p.fix_az:
    center = (fix_azimuth['az'], fix_azimuth['el'])
else:
    center = qubic.equ2gal(d['RA_center'], d['DEC_center'])

# Make TOD
if multiband:
    Nbfreq_in, nus_edge_in, nus_in, deltas_in, Delta_in, Nbbands_in = qubic.compute_freq(d['filter_nu'] / 1e9,
                                                                                         d['nf_sub'],
                                                                                         d['filter_relative_bandwidth'])
    a = qubic.QubicMultibandAcquisition(q, p, s, d, nus_edge_in)
else:
    a = qubic.QubicAcquisition(q, p, s, d)
TOD = a.get_observation(x0, noiseless=True, convolution=False)

plt.plot(TOD[0, :])
plt.xlabel('pointing index')
plt.ylabel('TOD')
plt.show()

# Map making
if alaImager:
    nf_sub_rec = 1
    d['synthbeam_kmax'] = 0
    if oneComponent:
        d['kind'] = 'I'
    q = qubic.QubicInstrument(d)
    if sel_det:
        select_det(q, id_det, multiband=False)
    arec = qubic.QubicAcquisition(q, p, s, d)
else:
    nf_sub_rec = 2
    Nbfreq, nus_edge, nus, deltas, Delta, Nbbands = qubic.compute_freq(d['filter_nu'] / 1e9,
                                                                       nf_sub_rec,
                                                                       d['filter_relative_bandwidth'])

    arec = qubic.QubicMultibandAcquisition(q, p, s, d, nus_edge)

maps_recon, nit, error = arec.tod2map(TOD, d, cov=None)
hp.gnomview(maps_recon[:, component], rot=center, reso=15)
print(maps_recon.shape)

# Coverage
cov = arec.get_coverage()
hp.gnomview(cov, rot=center, reso=15)
cov = np.sum(cov, axis=0)
maxcov = np.max(cov)
unseen = cov < maxcov * 0.1

# Convolved maps
TOD_useless, maps_convolved = arec.get_observation(x0)
maps_convolved = np.array(maps_convolved)

diffmap = maps_convolved - maps_recon
maps_convolved[:, unseen, :] = hp.UNSEEN
maps_recon[:, unseen, :] = hp.UNSEEN
diffmap[:, unseen, :] = hp.UNSEEN

xname = ''
if alaImager == True:
    nf_sub_rec = 1
    xname = 'alaImager'

for istokes in [0, 1, 2]:
    plt.figure(istokes, figsize=(12, 12))
    xr = 0.1 * np.max(maps_recon[0, :, 0])
    for i in range(nf_sub_rec):
        im_in = hp.gnomview(maps_convolved[i, :, istokes], rot=center, reso=5, sub=(nf_sub_rec, 2, 2 * i + 1), min=-xr,
                            max=xr, title='Input ' + stokes[istokes] + ' SubFreq {}'.format(i),
                            return_projected_map=True)
        np.savetxt(resultDir + '/in_%s_%s_subfreq_%d_%s.dat' % (name, stokes[istokes], i, xname), im_in)
        im_old = hp.gnomview(maps_recon[i, :, istokes], rot=center, reso=5, sub=(nf_sub_rec, 2, 2 * i + 2), min=-xr,
                             max=xr, title='Output ' + stokes[istokes] + ' SubFreq {}'.format(i),
                             return_projected_map=True)
        np.savetxt(resultDir + '/out_%s_%s_subfreq_%d_%s.dat' % (name, stokes[istokes], i, xname), im_old)

    plt.savefig(resultDir + '/%s_map_%s_%s.png' % (name, stokes[istokes], xname), bbox_inches='tight')
    plt.clf()
    plt.close()

plt.figure(figsize=(15,8))
count = 1

if d['kind'] == 'I':
    xr = 0.01 * np.max(maps_recon[:])
    im_old = hp.gnomview(maps_recon[:], rot=center, reso=5, min=-xr, max=xr, title='Output ', return_projected_map=True,
                         hold=True, xsize=500)
    plt.show()
else:
    for istokes in range(3):
        plt.subplot(1, 3, count)
        xr = 0.009
        im_old = hp.gnomview(maps_recon[0, :, istokes], xsize=500, rot=center, reso=5, min=-xr, max=xr,
                             title='Output ' + stokes[istokes], return_projected_map=True, hold=True)
        count += 1
    plt.show()

    P = np.sqrt(maps_recon[:, 1] ** 2 + maps_recon[:, 2] ** 2)

    plt.figure(figsize=(15, 8))

    plt.subplot(1, 2, 1)
    hp.gnomview(P, xsize=500, rot=center, reso=5, title='Output P', return_projected_map=True, hold=True)
    plt.subplot(1, 2, 2)
    hp.gnomview(sb, rot=[0, 90], xsize=500, reso=5, title='Input ', return_projected_map=True, hold=True)
    plt.show()