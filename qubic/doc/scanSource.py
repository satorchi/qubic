from __future__ import division, print_function
import os
import qubic
from qubicpack.utilities import Qubic_DataDir
import healpy as hp
import numpy as np
import pylab as plt
import matplotlib as mpl
import sys


def select_det(q,id):
    id=[id]
    detector_i = q.detector[id]
    q.detector = detector_i
    return(q)


mpl.style.use('classic')
name='test_scan_source'
resultDir='%s'%name
alaImager=True
component=1 # Choose the component number to plot 
sel_det=True #True if you want to use one detector, False if you want to use all detectors in focal plane
id_det=232 # if sel_det == True, choose detector number
oneComponent=False # True if you want to study only I component, otherwise False if you study IQU


try:
    os.makedirs(resultDir)
except:
    pass

global_dir = Qubic_DataDir(datafile='instrument.py', datadir=os.environ['QUBIC_DATADIR'])
# INSTRUMENT
d = qubic.qubicdict.qubicDict()
d.read_from_file(global_dir+'dicts/global_source_oneDet.dict')

q = qubic.QubicMultibandInstrument(d)
p = qubic.get_pointing(d)
s = qubic.QubicScene(d)

fix_azimuth=d['fix_azimuth']

plt.clf()
plt.figure(figsize=(12,8))
plt.subplot(4,1,1)
plt.plot(p.time,p.azimuth, 'bo')
plt.ylabel('Azimuth')
plt.subplot(4,1,2)
plt.plot(p.time,p.elevation, 'bo')
plt.ylabel('Elevation')
plt.subplot(4,1,3)
plt.plot(p.time,p.pitch, 'bo')
plt.ylabel('pitch angle')
plt.subplot(4,1,4)
plt.plot(p.time,p.angle_hwp, 'bo')
plt.ylabel('HWP angle')
#plt.savefig(resultDir+'/%s_pointing.png'%name,bbox_inches='tight')

m0=np.zeros(12*d['nside']**2)
x0=np.zeros((d['nf_sub'],len(m0),3))
id=hp.pixelfunc.ang2pix(d['nside'], fix_azimuth['el'], fix_azimuth['az'],lonlat=True)
source=m0*0
source[id]=1
arcToRad=np.pi/(180*60.)
source=hp.sphtfunc.smoothing(source,fwhm=30*arcToRad)
x0[:,:,0]=source


if p.fix_az:
    center = (fix_azimuth['az'],fix_azimuth['el'])
else:
    center = qubic.equ2gal(d['RA_center'], d['DEC_center'])


Nbfreq_in, nus_edge_in, nus_in, deltas_in, Delta_in, Nbbands_in = qubic.compute_freq(d['filter_nu']/1e9, d['nf_sub'], d['filter_relative_bandwidth']) 
a = qubic.QubicMultibandAcquisition(q, p, s, d, nus_edge_in)
TOD, maps_convolved_useless = a.get_observation(x0, noiseless=True)


nf_sub_rec = 2
Nbfreq, nus_edge, nus, deltas, Delta, Nbbands = qubic.compute_freq(d['filter_nu']/1e9, nf_sub_rec, d['filter_relative_bandwidth']) 

arec = qubic.QubicMultibandAcquisition(q, p, s,d, nus_edge)
out=arec.get_coverage()

hp.gnomview(out[0,:], rot=center, reso = 15)

if alaImager==True:
    
    d['synthbeam_kmax']=0
    q = qubic.QubicMultibandInstrument(d)
    p= qubic.get_pointing(d)
    s = qubic.QubicScene(d)
    arec = qubic.QubicMultibandAcquisition(q, p, s,d, nus_edge)

maps_recon = arec.tod2map(TOD,d)

TOD_useless, maps_convolved = arec.get_observation(x0)
maps_convolved = np.array(maps_convolved)
cov = arec.get_coverage()
cov = np.sum(cov, axis=0)
maxcov = np.max(cov)
unseen = cov < maxcov*0.1
diffmap = maps_convolved - maps_recon
maps_convolved[:,unseen,:] = hp.UNSEEN
maps_recon[:,unseen,:] = hp.UNSEEN
diffmap[:,unseen,:] = hp.UNSEEN
stokes = ['I', 'Q', 'U'] 

xname=''
if alaImager==True:
    nf_sub_rec=1
    xname='alaImager'

for istokes in [0,1,2]:
    plt.figure(istokes,figsize=(12,12)) 
    xr=0.1*np.max(maps_recon[0,:,0])
    for i in range(nf_sub_rec):
        
        im_in=hp.gnomview(maps_convolved[i,:,istokes], rot=center, reso=5, sub=(nf_sub_rec,2,2*i+1), min=-xr, max=xr,title='Input '+stokes[istokes]+' SubFreq {}'.format(i), return_projected_map=True)
        np.savetxt(resultDir+'/in_%s_%s_subfreq_%d_%s.dat'%(name,stokes[istokes],i,xname),im_in)
        im_old=hp.gnomview(maps_recon[i,:,istokes], rot=center, reso=5,sub=(nf_sub_rec,2,2*i+2), min=-xr, max=xr,title='Output '+stokes[istokes]+' SubFreq {}'.format(i), return_projected_map=True)
        np.savetxt(resultDir+'/out_%s_%s_subfreq_%d_%s.dat'%(name,stokes[istokes],i,xname),im_old)

    plt.savefig(resultDir+'/%s_map_%s_%s.png'%(name,stokes[istokes],xname),bbox_inches='tight')
    plt.clf()
    plt.close()