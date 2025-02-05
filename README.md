# Can GNNs Perform Temporal Edge Regression Tasks? A Case Study on Agricultural Trade Between Nations

## Set up

0. Create python environment, e.g., `conda create -n dgb python=3.9`

1. Run `source install.sh`

   

## Run regression

You can find all scripts in `run.sh`

### The basic scripts for dynamic GNN is as follows:

```{bash}
data=UNtrade
n_runs=1

# TGN
method=tgn
prefix="${method}_attn"
python tgn/train_self_supervised.py -d $data --use_memory --prefix "$prefix" --n_runs "$n_runs" --gpu 0

# JODIE
method=jodie
prefix="${method}_rnn"
python tgn/train_tgn_regression.py -d $data --use_memory --memory_updater rnn --embedding_module time --prefix "$prefix" --n_runs "$n_runs" --gpu 0

# DyRep
method=dyrep
prefix="${method}_rnn"
python tgn/train_tgn_regression.py -d "$data" --use_memory --memory_updater rnn --dyrep --use_destination_embedding_in_message --prefix "$prefix" --n_runs "$n_runs" --gpu 0

```

### The following normalization methods are available:
```{bash}
# Just choose one of them is fine!

--max_normalization

--logarithmize_weights

--node_out_normalization

(--node_in_normalization)
```

### If do NOT want to use negative sampler:
```{bash}
--no_negative_sampling
```

### If you want to train on all edges, use the following together:
```{bash}
--no_negative_sampling --fill_all_edges 
```

### If want to run baselines
```{bash}
--do_baseline
```

### To run static GNN:

```bash
python gcn/train_gcn_regression.py -d "UNtrade"
```

and don't forget to add a normalization method. 



## Run classification

```bash
data=UNtrade
n_runs=1

#baseline 
python tgn/train_tgn_classification.py -d $data --use_memory --prefix "$prefix" --n_runs 1 --gpu 0 --n_epoch 1 --num_class 10 --do_baseline

# TGN
method=tgn
prefix="${method}_attn"
python tgn/train_tgn_classification.py -d $data --use_memory --prefix "$prefix" --n_runs "$n_runs" --gpu 0 --n_epoch 200 --num_class 10 

# Jodie
method=jodie
prefix="${method}_rnn"
python tgn/train_tgn_classification.py -d $data --use_memory --memory_updater rnn --embedding_module time --prefix "$prefix" --n_runs "$n_runs" --gpu 0 --n_epoch 200 --num_class 10

#Dyrep
method=dyrep
prefix="${method}_rnn"
python tgn/train_tgn_classification.py -d "$data" --use_memory --memory_updater rnn --dyrep --use_destination_embedding_in_message --prefix "$prefix" --n_runs "$n_runs" --gpu 0 --n_epoch 200 --num_class 10
```

### If do NOT want to use negative sampler:

```bash
--no_negative_sampling
```

## Acknowledgement

We would like to thank our supervisors [Shenyang (Andy) Huang](https://www.cs.mcgill.ca/~shuang43/) and Dr.[Farimah Poursafaei](https://scholar.google.ca/citations?user=gZ7HEsMAAAAJ&hl=en) for their kindly supports and the course lecturers Dr.[Petar Veličković](https://petar-v.com/) and Dr.[Pietro Liò](https://www.cl.cam.ac.uk/~pl219/) for their great teaching. We also thank the authors for providing the code access to [DGB](https://github.com/fpour/DGB) and [TGN](https://github.com/twitter-research/tgn). 
