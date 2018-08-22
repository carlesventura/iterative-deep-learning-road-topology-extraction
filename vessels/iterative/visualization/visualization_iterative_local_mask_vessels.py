__author__ = 'carlesv'
from PIL import Image
import torch
from torch.autograd import Variable
import Nets as nt
import os
from astropy.stats import sigma_clipped_stats
from photutils import find_peaks
import numpy as np
import vessels.patch.bifurcations_toolbox as tb
from astropy.table import Table
import matplotlib.pyplot as plt
import vessels.iterative.shortest_path as sp
import networkx as nx
from scipy import ndimage
from skimage.morphology import skeletonize


def get_most_confident_outputs(img_id, patch_center_row, patch_center_col, confident_th, gpu_id, connected_same_vessel):

    patch_size = 64
    center = (patch_center_col, patch_center_row)

    x_tmp = int(center[0]-patch_size/2)
    y_tmp = int(center[1]-patch_size/2)

    confident_connections = {}
    confident_connections['x_peak'] = []
    confident_connections['y_peak'] = []
    confident_connections['peak_value'] = []

    root_dir = '/scratch_net/boxy/carlesv/gt_dbs/DRIVE/'
    img = Image.open(os.path.join(root_dir, 'test', 'images', '%02d_test.tif' % img_id))
    img = np.array(img, dtype=np.float32)
    h, w = img.shape[:2]

    if x_tmp > 0 and y_tmp > 0 and x_tmp+patch_size < w and y_tmp+patch_size < h:

        img_crop = img[y_tmp:y_tmp+patch_size,x_tmp:x_tmp+patch_size,:]

        img_crop = img_crop.transpose((2, 0, 1))
        img_crop = torch.from_numpy(img_crop)
        img_crop = img_crop.unsqueeze(0)

        inputs = img_crop / 255 - 0.5

        # Forward pass of the mini-batch
        inputs = Variable(inputs)

        #gpu_id = int(os.environ['SGE_GPU'])  # Select which GPU, -1 if CPU
        #gpu_id = -1
        if gpu_id >= 0:
            #torch.cuda.set_device(device=gpu_id)
            inputs = inputs.cuda()

        p = {}
        p['useRandom'] = 1  # Shuffle Images
        p['useAug'] = 0  # Use Random rotations in [-30, 30] and scaling in [.75, 1.25]
        p['inputRes'] = (64, 64)  # Input Resolution
        p['outputRes'] = (64, 64)  # Output Resolution (same as input)
        p['g_size'] = 64  # Higher means narrower Gaussian
        p['trainBatch'] = 1  # Number of Images in each mini-batch
        p['numHG'] = 2  # Number of Stacked Hourglasses
        p['Block'] = 'ConvBlock'  # Select: 'ConvBlock', 'BasicBlock', 'BottleNeck'
        p['GTmasks'] = 0 # Use GT Vessel Segmentations as input instead of Retinal Images
        model_dir = '/scratch_net/boxy/carlesv/HourGlasses_experiments/Iterative_margin_6/'
        if connected_same_vessel:
            modelName = tb.construct_name(p, "HourGlass-connected-same-vessel")
        else:
            modelName = tb.construct_name(p, "HourGlass-connected")
        #modelName = tb.construct_name(p, "HourGlass-connected-same-vessel-wo-bifurcations")
        numHGScales = 4  # How many times to downsample inside each HourGlass
        net = nt.Net_SHG(p['numHG'], numHGScales, p['Block'], 128, 1)
        epoch = 1800
        net.load_state_dict(torch.load(os.path.join(model_dir, os.path.join(model_dir, modelName+'_epoch-'+str(epoch)+'.pth')),
                                   map_location=lambda storage, loc: storage))

        if gpu_id >= 0:
            net = net.cuda()

        output = net.forward(inputs)
        pred = np.squeeze(np.transpose(output[len(output)-1].cpu().data.numpy()[0, :, :, :], (1, 2, 0)))


        mean, median, std = sigma_clipped_stats(pred, sigma=3.0)
        threshold = median + (10.0 * std)
        sources = find_peaks(pred, threshold, box_size=3)

        indxs = np.argsort(sources['peak_value'])
        for ii in range(0,len(indxs)):
            idx = indxs[len(indxs)-1-ii]
            if sources['peak_value'][idx] > confident_th:
                confident_connections['x_peak'].append(sources['x_peak'][idx])
                confident_connections['y_peak'].append(sources['y_peak'][idx])
                confident_connections['peak_value'].append(sources['peak_value'][idx])
            else:
                break

        confident_connections = Table([confident_connections['x_peak'], confident_connections['y_peak'], confident_connections['peak_value']], names=('x_peak', 'y_peak', 'peak_value'))

    return confident_connections

def get_most_confident_outputs_vessel_width(img_id, patch_center_row, patch_center_col, confident_th, gpu_id, connected_same_vessel):

    patch_size = 64
    center = (patch_center_col, patch_center_row)

    x_tmp = int(center[0]-patch_size/2)
    y_tmp = int(center[1]-patch_size/2)

    confident_connections = {}
    confident_connections['x_peak'] = []
    confident_connections['y_peak'] = []
    confident_connections['peak_value'] = []

    root_dir = '/scratch_net/boxy/carlesv/gt_dbs/DRIVE/'
    img = Image.open(os.path.join(root_dir, 'test', 'images', '%02d_test.tif' % img_id))
    img = np.array(img, dtype=np.float32)
    h, w = img.shape[:2]

    if x_tmp > 0 and y_tmp > 0 and x_tmp+patch_size < w and y_tmp+patch_size < h:

        img_crop = img[y_tmp:y_tmp+patch_size,x_tmp:x_tmp+patch_size,:]

        img_crop = img_crop.transpose((2, 0, 1))
        img_crop = torch.from_numpy(img_crop)
        img_crop = img_crop.unsqueeze(0)

        inputs = img_crop / 255 - 0.5

        # Forward pass of the mini-batch
        inputs = Variable(inputs)

        #gpu_id = int(os.environ['SGE_GPU'])  # Select which GPU, -1 if CPU
        #gpu_id = -1
        if gpu_id >= 0:
            #torch.cuda.set_device(device=gpu_id)
            inputs = inputs.cuda()

        p = {}
        p['useRandom'] = 1  # Shuffle Images
        p['useAug'] = 0  # Use Random rotations in [-30, 30] and scaling in [.75, 1.25]
        p['inputRes'] = (64, 64)  # Input Resolution
        p['outputRes'] = (64, 64)  # Output Resolution (same as input)
        p['g_size'] = 64  # Higher means narrower Gaussian
        p['trainBatch'] = 1  # Number of Images in each mini-batch
        p['numHG'] = 2  # Number of Stacked Hourglasses
        p['Block'] = 'ConvBlock'  # Select: 'ConvBlock', 'BasicBlock', 'BottleNeck'
        p['GTmasks'] = 0 # Use GT Vessel Segmentations as input instead of Retinal Images
        model_dir = '/scratch_net/boxy/carlesv/HourGlasses_experiments/Iterative_margin_6/'
        if connected_same_vessel:
            modelName = tb.construct_name(p, "HourGlass-connected-same-vessel")
        else:
            modelName = tb.construct_name(p, "HourGlass-connected")
        #modelName = tb.construct_name(p, "HourGlass-connected-same-vessel-wo-bifurcations")
        numHGScales = 4  # How many times to downsample inside each HourGlass
        net = nt.Net_SHG(p['numHG'], numHGScales, p['Block'], 128, 1)
        epoch = 1800
        net.load_state_dict(torch.load(os.path.join(model_dir, os.path.join(model_dir, modelName+'_epoch-'+str(epoch)+'.pth')),
                                   map_location=lambda storage, loc: storage))

        if gpu_id >= 0:
            net.cuda()

        output = net.forward(inputs)
        pred = np.squeeze(np.transpose(output[len(output)-1].cpu().data.numpy()[0, :, :, :], (1, 2, 0)))


        mean, median, std = sigma_clipped_stats(pred, sigma=3.0)
        threshold = median + (10.0 * std)
        sources = find_peaks(pred, threshold, box_size=3)

        results_dir_vessels = '/scratch_net/boxy/carlesv/HourGlasses_experiments/Iterative_margin_6/results_DRIU_vessel_segmentation/'

        pred_vessels = Image.open(results_dir_vessels + '%02d_test.png' %(img_id))
        pred_vessels = np.array(pred_vessels)
        pred_vessels = pred_vessels[y_tmp:y_tmp+patch_size,x_tmp:x_tmp+patch_size]


        for ii in range(0,len(sources['peak_value'])):

            mask = np.zeros((patch_size,patch_size))
            mask[int(sources['y_peak'][ii]),int(sources['x_peak'][ii])] = 1
            mask = ndimage.grey_dilation(mask, size=(5,5))
            pred_vessels_masked = np.ma.masked_array(pred_vessels, mask=(mask == 0))
            confidence_width = pred_vessels_masked.sum()
            #sources['peak_value'][ii] = sources['peak_value'][ii] + confidence_width
            if sources['peak_value'][ii] > confident_th:
                sources['peak_value'][ii] = confidence_width


        indxs = np.argsort(sources['peak_value'])
        for ii in range(0,len(indxs)):
            idx = indxs[len(indxs)-1-ii]
            if sources['peak_value'][idx] > confident_th:
                confident_connections['x_peak'].append(sources['x_peak'][idx])
                confident_connections['y_peak'].append(sources['y_peak'][idx])
                confident_connections['peak_value'].append(sources['peak_value'][idx])
            else:
                break

        confident_connections = Table([confident_connections['x_peak'], confident_connections['y_peak'], confident_connections['peak_value']], names=('x_peak', 'y_peak', 'peak_value'))

    return confident_connections

def get_most_confident_outputs_vessel_width_and_path_novelty(img_id, patch_center_row, patch_center_col, mask_graph, confident_th, gpu_id, connected_same_vessel):

    patch_size = 64
    center = (patch_center_col, patch_center_row)

    x_tmp = int(center[0]-patch_size/2)
    y_tmp = int(center[1]-patch_size/2)

    confident_connections = {}
    confident_connections['x_peak'] = []
    confident_connections['y_peak'] = []
    confident_connections['width_value'] = []
    confident_connections['novelty_value'] = []
    confident_connections['peak_value'] = []

    root_dir = '/scratch_net/boxy/carlesv/gt_dbs/DRIVE/'
    img = Image.open(os.path.join(root_dir, 'test', 'images', '%02d_test.tif' % img_id))
    img = np.array(img, dtype=np.float32)
    h, w = img.shape[:2]

    if x_tmp > 0 and y_tmp > 0 and x_tmp+patch_size < w and y_tmp+patch_size < h:

        img_crop = img[y_tmp:y_tmp+patch_size,x_tmp:x_tmp+patch_size,:]

        img_crop = img_crop.transpose((2, 0, 1))
        img_crop = torch.from_numpy(img_crop)
        img_crop = img_crop.unsqueeze(0)

        inputs = img_crop / 255 - 0.5

        # Forward pass of the mini-batch
        inputs = Variable(inputs)

        #gpu_id = int(os.environ['SGE_GPU'])  # Select which GPU, -1 if CPU
        #gpu_id = -1
        if gpu_id >= 0:
            #torch.cuda.set_device(device=gpu_id)
            inputs = inputs.cuda()

        p = {}
        p['useRandom'] = 1  # Shuffle Images
        p['useAug'] = 0  # Use Random rotations in [-30, 30] and scaling in [.75, 1.25]
        p['inputRes'] = (64, 64)  # Input Resolution
        p['outputRes'] = (64, 64)  # Output Resolution (same as input)
        p['g_size'] = 64  # Higher means narrower Gaussian
        p['trainBatch'] = 1  # Number of Images in each mini-batch
        p['numHG'] = 2  # Number of Stacked Hourglasses
        p['Block'] = 'ConvBlock'  # Select: 'ConvBlock', 'BasicBlock', 'BottleNeck'
        p['GTmasks'] = 0 # Use GT Vessel Segmentations as input instead of Retinal Images
        model_dir = '/scratch_net/boxy/carlesv/HourGlasses_experiments/Iterative_margin_6/'
        if connected_same_vessel:
            modelName = tb.construct_name(p, "HourGlass-connected-same-vessel")
        else:
            modelName = tb.construct_name(p, "HourGlass-connected")
        #modelName = tb.construct_name(p, "HourGlass-connected-same-vessel-wo-bifurcations")
        numHGScales = 4  # How many times to downsample inside each HourGlass
        net = nt.Net_SHG(p['numHG'], numHGScales, p['Block'], 128, 1)
        epoch = 1800
        net.load_state_dict(torch.load(os.path.join(model_dir, os.path.join(model_dir, modelName+'_epoch-'+str(epoch)+'.pth')),
                                   map_location=lambda storage, loc: storage))

        if gpu_id >= 0:
            net.cuda()

        output = net.forward(inputs)
        pred = np.squeeze(np.transpose(output[len(output)-1].cpu().data.numpy()[0, :, :, :], (1, 2, 0)))


        mean, median, std = sigma_clipped_stats(pred, sigma=3.0)
        threshold = median + (10.0 * std)
        sources = find_peaks(pred, threshold, box_size=3)

        results_dir_vessels = '/scratch_net/boxy/carlesv/HourGlasses_experiments/Iterative_margin_6/results_DRIU_vessel_segmentation/'

        pred_vessels = Image.open(results_dir_vessels + '%02d_test.png' %(img_id))
        pred_vessels = np.array(pred_vessels)
        pred_vessels = pred_vessels[y_tmp:y_tmp+patch_size,x_tmp:x_tmp+patch_size]

        mask_graph_crop = mask_graph[y_tmp:y_tmp+patch_size,x_tmp:x_tmp+patch_size]
        mask_detected_vessels = np.ones((patch_size,patch_size))
        indxs_vessels = np.argwhere(mask_graph_crop==1)
        mask_detected_vessels[indxs_vessels[:,0],indxs_vessels[:,1]] = 0
        #G = sp.generate_graph_center(img_idx,center)
        G = sp.generate_graph_center_patch_size_min_confidence(img_idx, center, patch_size, 0)

        sources['width_value'] = np.zeros(len(sources['peak_value']))
        sources['novelty_value'] = np.zeros(len(sources['peak_value']))
        for ii in range(0,len(sources['peak_value'])):

            #vessel width confidence
            mask = np.zeros((patch_size,patch_size))
            mask[int(sources['y_peak'][ii]),int(sources['x_peak'][ii])] = 1
            mask = ndimage.grey_dilation(mask, size=(5,5))
            pred_vessels_masked = np.ma.masked_array(pred_vessels, mask=(mask == 0))
            confidence_width = pred_vessels_masked.sum()

            #path novelty confidence
            confidence_novelty = 0
            target_idx = 32*64 + 32
            source_idx = int(sources['y_peak'][ii])*64 + int(sources['x_peak'][ii])
            length, path = nx.bidirectional_dijkstra(G,source_idx,target_idx)
            dist_path = ndimage.distance_transform_edt(mask_detected_vessels)
            for jj in range(0,len(path)):
                row_idx = path[jj] / 64
                col_idx = path[jj] % 64
                novelty_pixel = dist_path[row_idx,col_idx]
                if novelty_pixel > 3:
                    confidence_novelty = confidence_novelty + 255


            #sources['peak_value'][ii] = sources['peak_value'][ii] + confidence_width
            if sources['peak_value'][ii] > confident_th:
                sources['peak_value'][ii] = confidence_width + confidence_novelty*25/len(path)

            sources['width_value'][ii] = confidence_width
            sources['novelty_value'][ii] = confidence_novelty*25/len(path)

        indxs = np.argsort(sources['peak_value'])
        for ii in range(0,len(indxs)):
            idx = indxs[len(indxs)-1-ii]
            if sources['peak_value'][idx] > confident_th:
                confident_connections['x_peak'].append(sources['x_peak'][idx])
                confident_connections['y_peak'].append(sources['y_peak'][idx])
                confident_connections['peak_value'].append(sources['peak_value'][idx])
                confident_connections['width_value'].append(sources['width_value'][idx])
                confident_connections['novelty_value'].append(sources['novelty_value'][idx])
            else:
                break

        confident_connections = Table([confident_connections['x_peak'], confident_connections['y_peak'], confident_connections['peak_value'], confident_connections['width_value'], confident_connections['novelty_value']], names=('x_peak', 'y_peak', 'peak_value', 'width_value', 'novelty_value'))

    return confident_connections

def get_most_confident_outputs_path_novelty(img_id, patch_center_row, patch_center_col, mask_graph, confident_th, gpu_id, connected_same_vessel):

    patch_size = 64
    center = (patch_center_col, patch_center_row)

    x_tmp = int(center[0]-patch_size/2)
    y_tmp = int(center[1]-patch_size/2)

    confident_connections = {}
    confident_connections['x_peak'] = []
    confident_connections['y_peak'] = []
    confident_connections['width_value'] = []
    confident_connections['novelty_value'] = []
    confident_connections['peak_value'] = []

    root_dir = '/scratch_net/boxy/carlesv/gt_dbs/DRIVE/'
    img = Image.open(os.path.join(root_dir, 'test', 'images', '%02d_test.tif' % img_id))
    img = np.array(img, dtype=np.float32)
    h, w = img.shape[:2]

    if x_tmp > 0 and y_tmp > 0 and x_tmp+patch_size < w and y_tmp+patch_size < h:

        img_crop = img[y_tmp:y_tmp+patch_size,x_tmp:x_tmp+patch_size,:]

        img_crop = img_crop.transpose((2, 0, 1))
        img_crop = torch.from_numpy(img_crop)
        img_crop = img_crop.unsqueeze(0)

        inputs = img_crop / 255 - 0.5

        # Forward pass of the mini-batch
        inputs = Variable(inputs)

        #gpu_id = int(os.environ['SGE_GPU'])  # Select which GPU, -1 if CPU
        #gpu_id = -1
        if gpu_id >= 0:
            #torch.cuda.set_device(device=gpu_id)
            inputs = inputs.cuda()

        p = {}
        p['useRandom'] = 1  # Shuffle Images
        p['useAug'] = 0  # Use Random rotations in [-30, 30] and scaling in [.75, 1.25]
        p['inputRes'] = (64, 64)  # Input Resolution
        p['outputRes'] = (64, 64)  # Output Resolution (same as input)
        p['g_size'] = 64  # Higher means narrower Gaussian
        p['trainBatch'] = 1  # Number of Images in each mini-batch
        p['numHG'] = 2  # Number of Stacked Hourglasses
        p['Block'] = 'ConvBlock'  # Select: 'ConvBlock', 'BasicBlock', 'BottleNeck'
        p['GTmasks'] = 0 # Use GT Vessel Segmentations as input instead of Retinal Images
        model_dir = '/scratch_net/boxy/carlesv/HourGlasses_experiments/Iterative_margin_6/'
        if connected_same_vessel:
            modelName = tb.construct_name(p, "HourGlass-connected-same-vessel")
        else:
            modelName = tb.construct_name(p, "HourGlass-connected")
        #modelName = tb.construct_name(p, "HourGlass-connected-same-vessel-wo-bifurcations")
        numHGScales = 4  # How many times to downsample inside each HourGlass
        net = nt.Net_SHG(p['numHG'], numHGScales, p['Block'], 128, 1)
        epoch = 1800
        net.load_state_dict(torch.load(os.path.join(model_dir, os.path.join(model_dir, modelName+'_epoch-'+str(epoch)+'.pth')),
                                   map_location=lambda storage, loc: storage))

        if gpu_id >= 0:
            net.cuda()

        output = net.forward(inputs)
        pred = np.squeeze(np.transpose(output[len(output)-1].cpu().data.numpy()[0, :, :, :], (1, 2, 0)))


        mean, median, std = sigma_clipped_stats(pred, sigma=3.0)
        threshold = median + (10.0 * std)
        sources = find_peaks(pred, threshold, box_size=3)

        results_dir_vessels = '/scratch_net/boxy/carlesv/HourGlasses_experiments/Iterative_margin_6/results_DRIU_vessel_segmentation/'

        pred_vessels = Image.open(results_dir_vessels + '%02d_test.png' %(img_id))
        pred_vessels = np.array(pred_vessels)
        pred_vessels = pred_vessels[y_tmp:y_tmp+patch_size,x_tmp:x_tmp+patch_size]

        mask_graph_crop = mask_graph[y_tmp:y_tmp+patch_size,x_tmp:x_tmp+patch_size]
        mask_detected_vessels = np.ones((patch_size,patch_size))
        indxs_vessels = np.argwhere(mask_graph_crop==1)
        mask_detected_vessels[indxs_vessels[:,0],indxs_vessels[:,1]] = 0
        #G = sp.generate_graph_center(img_idx,center)
        G = sp.generate_graph_center_patch_size_min_confidence(img_idx, center, patch_size, 0)

        sources['width_value'] = np.zeros(len(sources['peak_value']))
        sources['novelty_value'] = np.zeros(len(sources['peak_value']))
        for ii in range(0,len(sources['peak_value'])):

            #path novelty confidence
            confidence_novelty = 0
            target_idx = 32*64 + 32
            source_idx = int(sources['y_peak'][ii])*64 + int(sources['x_peak'][ii])
            length, path = nx.bidirectional_dijkstra(G,source_idx,target_idx)
            dist_path = ndimage.distance_transform_edt(mask_detected_vessels)
            for jj in range(0,len(path)):
                row_idx = path[jj] / 64
                col_idx = path[jj] % 64
                novelty_pixel = dist_path[row_idx,col_idx]
                if novelty_pixel > 3:
                    confidence_novelty = confidence_novelty + 255


            #sources['peak_value'][ii] = sources['peak_value'][ii] + confidence_width
            if sources['peak_value'][ii] > confident_th:
                sources['peak_value'][ii] = confidence_novelty*25/len(path)

            sources['width_value'][ii] = 0
            sources['novelty_value'][ii] = confidence_novelty*25/len(path)

        indxs = np.argsort(sources['peak_value'])
        for ii in range(0,len(indxs)):
            idx = indxs[len(indxs)-1-ii]
            if sources['peak_value'][idx] > confident_th:
                confident_connections['x_peak'].append(sources['x_peak'][idx])
                confident_connections['y_peak'].append(sources['y_peak'][idx])
                confident_connections['peak_value'].append(sources['peak_value'][idx])
                confident_connections['width_value'].append(sources['width_value'][idx])
                confident_connections['novelty_value'].append(sources['novelty_value'][idx])
            else:
                break

        confident_connections = Table([confident_connections['x_peak'], confident_connections['y_peak'], confident_connections['peak_value'], confident_connections['width_value'], confident_connections['novelty_value']], names=('x_peak', 'y_peak', 'peak_value', 'width_value', 'novelty_value'))

    return confident_connections

start_row_all = np.array([312, 312, 330, 270, 330, 336, 349, 216, 348, 351, 325, 322, 342, 359, 318, 337, 348, 373, 349, 367])
start_col_all = np.array([91, 442, 99, 297, 100, 476, 442, 451, 109, 462, 99, 98, 489, 495, 242, 461, 449, 446, 491, 458])


connected_same_vessel = False
confidence_network = False
confidence_width = True
confidence_novelty = False
confidence_width_and_novelty = False

#gpu_id = int(os.environ['SGE_GPU'])  # Select which GPU, -1 if CPU
gpu_id = -1
if gpu_id >= 0:
    torch.cuda.set_device(device=gpu_id)

#img_idx = 1

for img_idx in range(1,21):

    print(img_idx)

    start_row = start_row_all[img_idx-1]
    start_col = start_col_all[img_idx-1]

    root_dir = '/scratch_net/boxy/carlesv/gt_dbs/DRIVE/'
    img = Image.open(os.path.join(root_dir, 'test', 'images', '%02d_test.tif' % img_idx))

    img_array = np.array(img, dtype=np.float32)
    h, w = img_array.shape[:2]

    center_points = []
    center = (start_col, start_row)
    center_points.append(center)
    confident_th = 25

    #colors = ['red', 'blue', 'black', 'green', 'purple']
    colors = ['red', 'blue', 'cyan', 'green', 'purple']

    mask = np.zeros((h,w))
    mask_outputs = np.zeros((h,w))
    mask_iter = np.zeros((h,w))



    pending_connections_x = []
    pending_connections_y = []
    parent_connections_x = []
    parent_connections_y = []

    confidence_pending_connections = []
    pending_connections_x.append(center[0])
    pending_connections_y.append(center[1])
    confidence_pending_connections.append(255)
    mask_graph = np.zeros((h,w))

    connections_to_be_extended = []
    connections_to_be_extended.append(True)

    parent_connections_x.append(center[0])
    parent_connections_y.append(center[1])

    parent_map = {}
    location_map = {}
    current_id = 0

    parent_map[current_id] = -1
    location_map[current_id] = center

    offset = 2
    offset_mask = 0
    offset_local_mask = 10
    mask_outputs[center[1]-offset_mask:center[1]+offset_mask+1,center[0]-offset_mask:center[0]+offset_mask+1] = 1

    count = 0
    #for ii in range(0,10000):
    ii = 0
    while len(pending_connections_x) > 0:
        max_idx = np.argmax(confidence_pending_connections)
        next_element_x = pending_connections_x[max_idx]
        next_element_y = pending_connections_y[max_idx]

        if ii > 0:

            previous_center_x = parent_connections_x[max_idx]
            previous_center_y = parent_connections_y[max_idx]

            tmp_center = (previous_center_x,previous_center_y)
            G = sp.generate_graph_center(img_idx,tmp_center)
            #G = sp.generate_graph_center_connectivity4(img_idx,tmp_center)
            target_idx = 32*64 + 32
            source_idx = (next_element_y-previous_center_y+32)*64 + next_element_x-previous_center_x+32
            length, path = nx.bidirectional_dijkstra(G,source_idx,target_idx)
            pos_y_vector = []
            pos_x_vector = []
            for jj in range(0,len(path)):
                row_idx = path[jj] / 64
                col_idx = path[jj] % 64
                global_x = col_idx+previous_center_x-32
                global_y = row_idx+previous_center_y-32
                if mask_graph[global_y,global_x] == 0:
                    pos_y_vector.append(global_y)
                    pos_x_vector.append(global_x)
                else:
                    break


            if len(pos_y_vector) > 0:
                new_segment = []
                #if visualize_graph:
                    #plt.plot(next_element_x,next_element_y,marker='o',color=colors[count%5])
                for kk in range(0,len(pos_y_vector)):
                    #mask_graph[pos_y_vector[kk],pos_x_vector[kk]] = 1
                    mask_graph[pos_y_vector[kk]-offset:pos_y_vector[kk]+offset+1,pos_x_vector[kk]-offset:pos_x_vector[kk]+offset+1] = 1
                    mask_iter[pos_y_vector[kk]-offset:pos_y_vector[kk]+offset+1,pos_x_vector[kk]-offset:pos_x_vector[kk]+offset+1] = ii
                #if visualize_graph:
                    #plt.scatter(pos_x_vector,pos_y_vector,color=colors[count%5],marker='+')
                count += 1



        #if ii%1 == 0:
        #if ii < 20 or (ii < 200 and ii % 20 == 0) or ii % 100 == 0:
        #if ii > 200 and ii % 100 == 0:
            #print(ii)
            #scipy.misc.imsave('/scratch_net/boxy/carlesv/results/DRIVE/tmp_results/pred_graph_%02d_mask_same_mask_graph_th_30_with_novelty_iter_%05d.png' % (img_idx,ii), mask_graph)
            #scipy.misc.imsave('/scratch_net/boxy/carlesv/results/DRIVE/tmp_results/pred_graph_%02d_mask_same_mask_graph_th_30_with_novelty_iter_%05d_outputs.png' % (img_idx,ii), mask_outputs)
            #scipy.misc.imsave('/scratch_net/boxy/carlesv/results/DRIVE/tmp_results/pred_graph_%02d_mask_same_mask_graph_th_30_only_novelty_iter_%05d.png' % (img_idx,ii), mask_graph)
            #scipy.misc.imsave('/scratch_net/boxy/carlesv/results/DRIVE/tmp_results/pred_graph_%02d_mask_same_mask_graph_th_30_only_novelty_iter_%05d_outputs.png' % (img_idx,ii), mask_outputs)
            #plt.figure(figsize=(6,6))
            #plt.figure(figsize=(12,12), dpi=160)
            #plt.imshow(img)
            #mask_graph_skeleton = skeletonize(mask_graph>0)
            #indxs = np.argwhere(mask_graph_skeleton==1)
            #plt.scatter(indxs[:,1],indxs[:,0],color='green',marker='+')
            #plt.axis('off')
            #plt.savefig('/scratch_net/boxy/carlesv/results/DRIVE/iterative_visualization_results/%02d_test_iter_%05d.png' % (img_idx,ii), bbox_inches='tight')
            #plt.close()
            #plt.show()



        confidence_pending_connections = np.delete(confidence_pending_connections,max_idx)
        pending_connections_x = np.delete(pending_connections_x,max_idx)
        pending_connections_y = np.delete(pending_connections_y,max_idx)

        parent_connections_x = np.delete(parent_connections_x,max_idx)
        parent_connections_y = np.delete(parent_connections_y,max_idx)

        parent_id = current_id

        to_be_extended = connections_to_be_extended[max_idx]
        connections_to_be_extended = np.delete(connections_to_be_extended,max_idx)

        if to_be_extended:

            if confidence_network:
                confident_connections = get_most_confident_outputs(img_idx, next_element_y, next_element_x, confident_th, gpu_id, connected_same_vessel)
            elif confidence_width:
                confident_connections = get_most_confident_outputs_vessel_width(img_idx, next_element_y, next_element_x, confident_th, gpu_id, connected_same_vessel)
            elif confidence_novelty:
                confident_connections = get_most_confident_outputs_path_novelty(img_idx, next_element_y, next_element_x, mask_graph, confident_th, gpu_id, connected_same_vessel)
            else:
                confident_connections = get_most_confident_outputs_vessel_width_and_path_novelty(img_idx, next_element_y, next_element_x, mask_graph, confident_th, gpu_id, connected_same_vessel)

            #print(next_element_x)
            #print(next_element_y)

            #for kk in range(0,len(confident_connections)):
            for kk in range(0,len(confident_connections['peak_value'])):
                tmp_x = confident_connections['x_peak'][kk]+next_element_x-32
                tmp_y = confident_connections['y_peak'][kk]+next_element_y-32
                local_mask = np.zeros((h,w))
                if parent_id in parent_map.keys():
                    grandparent_id = parent_map[parent_id]
                    if grandparent_id != -1:
                        location_grandparent = location_map[grandparent_id]
                        min_y = np.max([0, location_grandparent[1]-offset_local_mask])
                        min_x = np.max([0, location_grandparent[0]-offset_local_mask])
                        max_y = np.min([h-1, location_grandparent[1]+offset_local_mask+1])
                        max_x = np.min([w-1, location_grandparent[0]+offset_local_mask+1])
                        local_mask[min_y:max_y,min_x:max_x] = 1

                if local_mask[tmp_y,tmp_x] == 0 and mask_graph[tmp_y,tmp_x] == 0:

                    pending_connections_x = np.append(pending_connections_x,tmp_x)
                    pending_connections_y = np.append(pending_connections_y,tmp_y)
                    confidence_pending_connections = np.append(confidence_pending_connections,confident_connections['peak_value'][kk])

                    parent_connections_x = np.append(parent_connections_x,next_element_x)
                    parent_connections_y = np.append(parent_connections_y,next_element_y)

                    current_id += 1
                    parent_map[current_id] = parent_id
                    location_map[current_id] = (tmp_x, tmp_y)

                    connections_to_be_extended = np.append(connections_to_be_extended,True)

                elif local_mask[tmp_y,tmp_x] == 0 and mask_graph[tmp_y,tmp_x] == 1:

                    pending_connections_x = np.append(pending_connections_x,tmp_x)
                    pending_connections_y = np.append(pending_connections_y,tmp_y)
                    confidence_pending_connections = np.append(confidence_pending_connections,confident_connections['peak_value'][kk])

                    parent_connections_x = np.append(parent_connections_x,next_element_x)
                    parent_connections_y = np.append(parent_connections_y,next_element_y)

                    current_id += 1
                    parent_map[current_id] = parent_id
                    location_map[current_id] = (tmp_x, tmp_y)

                    connections_to_be_extended = np.append(connections_to_be_extended,False)


        ii += 1


    plt.figure(figsize=(12,12), dpi=160)
    plt.imshow(img)
    mask_graph_skeleton = skeletonize(mask_graph>0)
    #indxs = np.argwhere(mask_graph==1)
    indxs = np.argwhere(mask_graph_skeleton==1)
    plt.scatter(indxs[:,1],indxs[:,0],color='green',marker='+')
    plt.axis('off')
    #plt.savefig('/scratch_net/boxy/carlesv/retinal/CVPR2018/figures/iterative_vessel_01_test_iter_%05d.png' % ii, bbox_inches='tight')
    plt.savefig('/scratch_net/boxy/carlesv/results/DRIVE/iterative_visualization_results/%02d_test_iter_final.png' % (img_idx), bbox_inches='tight')
    plt.close()


    #scipy.misc.imsave('/scratch_net/boxy/carlesv/results/DRIVE/tmp_results/pred_graph_%02d_mask_same_mask_graph_th_30_with_novelty_evolution.png' % (img_idx), mask_iter)
    #scipy.misc.imsave('/scratch_net/boxy/carlesv/results/DRIVE/tmp_results/pred_graph_%02d_mask_same_mask_graph_th_30_only_novelty_evolution.png' % (img_idx), mask_iter)








