# Iterative Deep Learning for Road Topology Extraction

Published at BMVC 2018.

Paper available on ArXiv: https://arxiv.org/abs/1808.09814

Paper website: https://carlesventura.github.io/iterative-dl-road-website/

## Code instructions

### Downloading datasets:

Download Massachusetts Roads Dataset from website: https://www.cs.toronto.edu/~vmnih/data/

Download DRIVE dataset (vessels from retina images) from website: https://www.isi.uu.nl/Research/Databases/DRIVE/

Download graph annotations for DRIVE dataset from website: http://people.duke.edu/~sf59/Estrada_TMI_2015_dataset.htm

Set your work directory, create a directory inside named gt_dbs and copy there the downloaded datasets (roads dataset in a folder named MassachusettsRoads, DRIVE dataset in a folder named DRIVE and graph annotations for DRIVE in a folder named artery-vein).

### Experiments for road topology extraction:

1. Generate road patches for training the patch-level model: [roads/patch/generate_gt_val_roads.py](roads/patch/generate_gt_val_roads.py)
2. Train patch-level model: [roads/patch/train_road_patches.py](roads/patch/train_road_patches.py)
3. (Optional) Evaluate patch-level model: [roads/patch/evaluation/PR_evaluation_patch_roads.py](roads/patch/evaluation/PR_evaluation_patch_roads.py)
4. Apply the patch-level model iteratively over the road test images: [roads/iterative/iterative_roads_local_mask.py](roads/iterative/iterative_roads_local_mask.py)
5. (Optional) Evaluate iterative results: [roads/iterative/evaluation/connectivity_evaluation_roads.py](roads/iterative/evaluation/connectivity_evaluation_roads.py)

### Experiments for vessel topology extraction:

1. Train patch-level model: [vessels/patch/train_hg.py](vessels/patch/train_hg.py)
2. (Optional) Evaluate patch-level model: [vessels/patch/evaluation/PR_evaluation.py](vessels/patch/evaluation/PR_evaluation.py)
3. Apply the patch-level model iteratively over the retina test images: [vessels/iterative/iterative_graph_creation_no_mask_offset.py](vessels/iterative/iterative_graph_creation_no_mask_offset.py)
4. (Optional) Evaluate iterative results: [vessels/iterative/evaluation/connectivity_evaluation.py](vessels/iterative/evaluation/connectivity_evaluation.py)
