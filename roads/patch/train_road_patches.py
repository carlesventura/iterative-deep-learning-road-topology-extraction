# Includes
import os
import numpy as np
import torch
from torch.autograd import Variable
import torch.nn as nn
import torch.optim as optim
from torchvision import transforms
from torch.utils.data import DataLoader
import Nets as nt
import timeit
import scipy.misc
from PIL import Image
import bifurcations_toolbox_roads as tbroads

# Setting of parameters
# Parameters in p are used for the name of the model

p = {}
p['useRandom'] = 1  # Shuffle Images
p['useAug'] = 0  # Use Random rotations in [-30, 30] and scaling in [.75, 1.25]
p['inputRes'] = (64, 64)  # Input Resolution
p['outputRes'] = (64, 64)  # Output Resolution (same as input)
p['g_size'] = 64  # Higher means narrower Gaussian
p['trainBatch'] = 1  # Number of Images in each mini-batch
p['numHG'] = 2  # Number of Stacked Hourglasses
p['Block'] = 'ConvBlock'  # Select: 'ConvBlock', 'BasicBlock', 'BottleNeck', 'BottleneckPreact'
p['GTmasks'] = 0 # Use GT Vessel Segmentations as input instead of Retinal Images

save_vertices_indxs = False

# Setting other parameters
nEpochs = 200  # Number of epochs for training
numHGScales = 4  # How many times to downsample inside each HourGlass
useVal = 1  # See evolution of the test set when training?
testBatch = 1  # Testing Batch
nTestInterval = 1  # Run on test set every nTestInterval iterations
#seq_names = ('1-left', '3-left', '2-left')
db_root_dir = '/scratch_net/boxy/carlesv/gt_dbs/MassachusettsRoads/'
#save_dir = '/scratch_net/boxy/carlesv/HourGlasses_experiments/roads/Iterative_margin_6/'
save_dir = '/scratch_net/boxy/carlesv/HourGlasses_experiments/roads/Iterative_margin_6_200_epoches/'
vis_net = 0  # Visualize your network?
if 'SGE_GPU' in os.environ.keys():
    gpu_id = int(os.environ['SGE_GPU'])  # Select which GPU, -1 if CPU
    print('GPU:'+str(gpu_id))
else:
    gpu_id = -1
snapshot = 10  # Store a model every snapshot epochs


# Network definition
net = nt.Net_SHG(p['numHG'], numHGScales, p['Block'], 128, 1)
if gpu_id >= 0:
    torch.cuda.set_device(device=gpu_id)
    net.cuda()

# Loss function definition
criterion = nn.MSELoss(size_average=True)

# Use the following optimizer
optimizer = optim.RMSprop(net.parameters(), lr=0.00005, alpha=0.99, momentum=0.0)
# optimizer = optim.SGD(net.parameters(), lr=0.01/1000, momentum=0.1)
# optimizer = optim.Adam(net.parameters(), lr=0.0005)


# Preparation of the data loaders
# Define augmentation transformations as a composition
#composed_transforms = transforms.Compose([tb.ScaleNRotate(rots=(-30, 30), scales=(.75, 1.25)), tb.RandomHorizontalFlip(), tb.ToTensor()])
if p['useAug'] == 1:
    #composed_transforms = transforms.Compose([tb.ScaleNRotate(rots=(-90, 90), scales=(.5, 1.5)), tb.ToTensor(), tb.normalize()])
    composed_transforms = transforms.Compose([tbroads.ScaleNRotate(rots=(-30, 30), scales=(.75, 1.25)), tbroads.ToTensor()])
else:
    composed_transforms = tbroads.ToTensor()

#composed_transforms_test = tbroads.ToTensor()

# Training dataset and its iterator
db_train = tbroads.ToolDataset(train=True, inputRes=p['inputRes'], outputRes=p['outputRes'],
                          sigma=float(p['outputRes'][0]) / p['g_size'],
                          db_root_dir=db_root_dir, transform=composed_transforms, save_vertices_indxs=False)
trainloader = DataLoader(db_train, batch_size=p['trainBatch'], shuffle=True)

num_img_tr = len(trainloader)

running_loss_tr = 0
running_loss_val = 0
loss_tr = []
loss_val = []


modelName = tbroads.construct_name(p, "HourGlass")


print("Training Network")
#file = open('/scratch_net/boxy/carlesv/HourGlasses_experiments/roads/Iterative_margin_6/logfile.txt', 'a')
#file_training_loss = open('/scratch_net/boxy/carlesv/HourGlasses_experiments/roads/Iterative_margin_6/training_loss.txt', 'a')
#file_validation_loss = open('/scratch_net/boxy/carlesv/HourGlasses_experiments/roads/Iterative_margin_6/validation_loss.txt', 'a')

file = open(save_dir + 'logfile.txt', 'a')
file_training_loss = open(save_dir + 'training_loss.txt', 'a')
file_validation_loss = open(save_dir + 'validation_loss.txt', 'a')

# Main Training and Testing Loop
for epoch in range(0, nEpochs):
    start_time = timeit.default_timer()
    file.write('Epoch %02d\n' % (epoch))
    file.flush()
    # One training epoch
    for ii, sample_batched in enumerate(trainloader):

        img, gt, valid_img = sample_batched['image'], sample_batched['gt'], sample_batched['valid_img']
        file.write('Image %02d\n' % (ii))
        file.flush()

        if int(valid_img.numpy()) == 1:
            inputs = img / 255 - 0.5
            gts = 255 * gt
            file.write('Image %02d being processed\n' % (ii))
            file.flush()

            # Forward-Backward of the mini-batch
            inputs, gts = Variable(inputs), Variable(gts)
            if gpu_id >= 0:
                inputs, gts = inputs.cuda(), gts.cuda()

            optimizer.zero_grad()
            outputs = net.forward(inputs)

            losses = [None] * p['numHG']
            for i in range(0, len(outputs)):
                losses[i] = criterion(outputs[i], gts)
            loss = sum(losses)

            running_loss_tr += loss.data[0]
            if ii % num_img_tr == num_img_tr-1:
                loss_tr.append(running_loss_tr/num_img_tr)
                print('[%d, %5d] training loss: %.5f' % (epoch+1, ii + 1, running_loss_tr/num_img_tr))
                file_training_loss.write('[%d, %5d] training loss: %.5f' % (epoch+1, ii + 1, running_loss_tr/num_img_tr))
                file_training_loss.flush()
                running_loss_tr = 0
            loss.backward()
            optimizer.step()

            if ii == len(trainloader)-1:
                pred = np.squeeze(np.transpose(outputs[len(outputs)-1].cpu().data.numpy()[0, :, :, :], (1, 2, 0)))
                #base_dir = '/scratch_net/boxy/carlesv/HourGlasses_experiments/roads/Iterative_margin_6/tmp_results_train/'
                base_dir = save_dir + 'tmp_results_train/'
                scipy.misc.imsave(base_dir + 'epoch_' + str(epoch) + '_train.png', pred)
                scipy.misc.imsave(base_dir + 'epoch_' + str(epoch) + '_gt.png', np.squeeze(gt.numpy()))
                np.save(base_dir + 'epoch_' + str(epoch) + '_gt.npy', np.squeeze(gt.numpy()))
                scipy.misc.imsave(base_dir + 'epoch_' + str(epoch) + '_img.png', np.transpose(np.squeeze(img.numpy()),(1,2,0)))

    # Save the model
    if (epoch % snapshot) == 0 and epoch != 0:
        torch.save(net.state_dict(), os.path.join(save_dir, modelName+'_epoch-'+str(epoch)+'.pth'))


    # One testing epoch
    if useVal:
        if epoch % nTestInterval == (nTestInterval-1):

            num_patches_per_image = 50
            num_images = 14
            num_img_val = num_patches_per_image*num_images

            for jj in range(0,num_patches_per_image):
                for ii in range(0,num_images):

                    val_dir = '/scratch_net/boxy/carlesv/HourGlasses_experiments/roads/Iterative_margin_6/val_gt/'
                    img = Image.open(os.path.join(val_dir, 'img_%02d_patch_%02d_img.png' %(ii+1,jj+1)))
                    img = np.array(img, dtype=np.float32)

                    if len(img.shape) == 2:
                        image_tmp = img
                        h, w = image_tmp.shape
                        img = np.zeros((h, w, 3))
                        img[:,:,0] = image_tmp
                        img[:,:,1] = image_tmp
                        img[:,:,2] = image_tmp
                    img = img.transpose((2, 0, 1))
                    img = torch.from_numpy(img)
                    img = img.unsqueeze(0)

                    inputs = img / 255 - 0.5

                    gt = Image.open(os.path.join(val_dir, 'img_%02d_patch_%02d_gt.png' %(ii+1,jj+1)))
                    #gt = composed_transforms_test(gt)
                    gt = np.array(gt)
                    if len(gt.shape) == 2:
                        gt_tmp = gt
                        h, w = gt_tmp.shape
                        gt = np.zeros((h, w, 1), np.float32)
                        gt[:,:,0] = gt_tmp

                    gt = gt.transpose((2, 0, 1))
                    gt = torch.from_numpy(gt)

                    gt = Variable(gt)
                    if gpu_id >= 0:
                        gt = gt.cuda()

                    # Forward pass of the mini-batch
                    inputs = Variable(inputs)
                    if gpu_id >= 0:
                        inputs = inputs.cuda()

                    output = net.forward(inputs)
                    #pred = np.squeeze(np.transpose(output[len(output)-1].cpu().data.numpy()[0, :, :, :], (1, 2, 0)))

                    losses = [None] * p['numHG']
                    for i in range(0, len(output)):
                        losses[i] = criterion(output[i], gt)
                    loss = sum(losses)

                    running_loss_val += loss.data[0]
                    if ii == num_images-1 and jj == num_patches_per_image-1:
                        loss_val.append(running_loss_val/num_img_val)
                        print('[%d, %5d] validation loss: %.5f' % (epoch+1, ii + 1, running_loss_val/num_img_val))
                        file_validation_loss.write('[%d, %5d] validation loss: %.5f' % (epoch+1, num_img_val, running_loss_val/num_img_val))
                        file_validation_loss.flush()
                        running_loss_val = 0


file.close()
# Separate interactive plotting of test set results
# plt.close("all")
# plt.ion()
# f, ax_arr = plt.subplots(1, 3)
# for ii, sample_batched in enumerate(testloader):
#     img, gt = sample_batched['image'], sample_batched['gt']
#     inputs = img / 255 - 0.5
#
#     # Forward pass of the mini-batch
#     inputs = Variable(inputs)
#     if gpu_id >= 0:
#         inputs = inputs.cuda()
#
#     output = net.forward(inputs)
#     for jj in range(int(img.size()[0])):
#         pred = np.transpose(output[len(output)-1].cpu().data.numpy()[jj, :, :, :], (1, 2, 0))
#         img_ = np.transpose(img.numpy()[jj, :, :, :], (1, 2, 0))
#         gt_ = np.transpose(gt.numpy()[jj, :, :, :], (1, 2, 0))
#         # Plot the particular example
#         ax_arr[0].cla()
#         ax_arr[1].cla()
#         ax_arr[2].cla()
#         ax_arr[0].set_title("Input Image")
#         ax_arr[1].set_title("Ground Truth")
#         ax_arr[2].set_title("Detection")
#         ax_arr[0].imshow(tb.im_normalize(img_))
#         ax_arr[1].imshow(gt_)
#         ax_arr[2].imshow(tb.im_normalize(pred))
#         plt.pause(0.001)


# Separate interactive plotting of training set results
# plt.close("all")
# plt.ion()
# f, ax_arr = plt.subplots(1, 3)
# for ii, sample_batched in enumerate(trainloader):
#     img, gt = sample_batched['image'], sample_batched['gt']
#     inputs = img / 255 - 0.5
#
#     # Forward pass of the mini-batch
#     inputs = Variable(inputs)
#     if gpu_id >= 0:
#         inputs = inputs.cuda()
#
#     output = net.forward(inputs)
#     for jj in range(int(img.size()[0])):
#         pred = np.transpose(output[len(output)-1].cpu().data.numpy()[jj, :, :, :], (1, 2, 0))
#         img_ = np.transpose(img.numpy()[jj, :, :, :], (1, 2, 0))
#         gt_ = np.transpose(gt.numpy()[jj, :, :, :], (1, 2, 0))
#         # Plot the particular example
#         ax_arr[0].cla()
#         ax_arr[1].cla()
#         ax_arr[2].cla()
#         ax_arr[0].set_title("Input Image")
#         ax_arr[1].set_title("Ground Truth")
#         ax_arr[2].set_title("Detection")
#         ax_arr[0].imshow(tb.im_normalize(img_))
#         ax_arr[1].imshow(gt_)
#         ax_arr[2].imshow(tb.im_normalize(pred))
#         plt.pause(0.001)

