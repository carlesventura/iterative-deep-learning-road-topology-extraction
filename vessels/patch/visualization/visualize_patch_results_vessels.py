__author__ = 'carlesv'
import matplotlib.pyplot as plt
from PIL import Image
from astropy.stats import sigma_clipped_stats
from photutils import find_peaks
import numpy as np
from shapely.geometry import LineString
import scipy.io as sio

dist_th = 4
num_images = 20
num_patches = 50
start_img = 1
patch_size = 64

#peak_th = 100

gt_base_dir = '/scratch_net/boxy/carlesv/HourGlasses_experiments/Iterative_margin_6/gt_test'
results_base_dir = '/scratch_net/boxy/carlesv/HourGlasses_experiments/Iterative_margin_6/results'

configs = ['_not_connected', '_connected', '_connected_same_vessel']

idx_patch = 3
num_patches = 50

f = open('/scratch_net/boxy/carlesv/gt_dbs/DRIVE/vertices_selected.txt','r')
count = 0

while count != (idx_patch-1)*num_images + start_img-1:
    line = f.readline()
    count += 1



#for idx in range(1,num_images+1):
for idx in range(start_img,start_img+num_images):

    print(idx)
    fig, axes = plt.subplots(1, 5)

    mat_contents = sio.loadmat('/scratch_net/boxy/carlesv/artery-vein/AV-DRIVE/test/%02d_manual1.mat' %idx)
    vertices = np.squeeze(mat_contents['G']['V'][0,0])-1
    subscripts = np.squeeze(mat_contents['G']['subscripts'][0,0])
    art = np.squeeze(mat_contents['G']['art'][0,0])
    ven = np.squeeze(mat_contents['G']['ven'][0,0])

    config_type = configs[0]
    retina_img = Image.open(gt_base_dir + config_type + '/img_%02d_patch_%02d_img.png' %(idx, idx_patch))
    axes[0].imshow(retina_img)
    axes[0].axis('off')

    line = f.readline()
    selected_vertex = int(line.split()[1])
    center = (vertices[selected_vertex,0], vertices[selected_vertex,1])

    x_tmp = int(center[0]-patch_size/2)
    y_tmp = int(center[1]-patch_size/2)

    for ii in range(0,len(subscripts)):
        segment = LineString([vertices[subscripts[ii,0]-1], vertices[subscripts[ii,1]-1]])
        xcoords, ycoords = segment.xy
        if art[subscripts[ii,0]-1] and art[subscripts[ii,1]-1]:
            axes[1].plot(xcoords-np.asarray(x_tmp), ycoords-np.asarray(y_tmp), color='red', alpha=0.5, linewidth=1, solid_capstyle='round', zorder=2)
        else:
            axes[1].plot(xcoords-np.asarray(x_tmp), ycoords-np.asarray(y_tmp), color='blue', alpha=0.5, linewidth=1, solid_capstyle='round', zorder=2)

    axes[1].set_xlim([0, patch_size-1])
    axes[1].set_ylim([patch_size-1,0])
    axes[1].set_aspect(1)
    axes[1].axis('off')




    for config_id in range(0,len(configs)):

        config_type = configs[config_id]



        pred = np.load(results_base_dir + config_type + '/epoch_1800/img_%02d_patch_%02d.npy' %(idx, idx_patch))



        mean, median, std = sigma_clipped_stats(pred, sigma=3.0)
        threshold = median + (10.0 * std)
        sources = find_peaks(pred, threshold, box_size=3)
        positions = (sources['x_peak'], sources['y_peak'])


        axes[config_id+2].imshow(pred, interpolation='nearest')
        axes[config_id+2].axis('off')
        #axes[2,config_id].plot(sources['x_peak'], sources['y_peak'], ls='none', color='red',marker='+', ms=10, lw=1.5)



    if config_id == len(configs)-1:
        plt.show()



