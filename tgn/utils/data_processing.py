import numpy as np
import random
import pandas as pd
from sklearn.preprocessing import MinMaxScaler
from tqdm import tqdm

class Data:
    def __init__(self, sources, destinations, timestamps, edge_idxs, labels, edge_features):
        self.sources = sources
        self.destinations = destinations
        self.timestamps = timestamps
        self.edge_idxs = edge_idxs
        self.labels = labels
        self.edge_features = edge_features
        self.n_interactions = len(sources)
        self.unique_nodes = set(sources) | set(destinations)
        self.n_unique_nodes = len(self.unique_nodes)


def get_data_node_classification(dataset_name, use_validation=False):
    ### Load data and train val test split
    graph_df = pd.read_csv('./data/ml_{}.csv'.format(dataset_name))
    edge_features = np.load('./data/ml_{}.npy'.format(dataset_name))
    node_features = np.load('./data/ml_{}_node.npy'.format(dataset_name))

    val_time, test_time = list(np.quantile(graph_df.ts, [0.70, 0.85]))

    sources = graph_df.u.values
    destinations = graph_df.i.values
    edge_idxs = graph_df.idx.values
    labels = graph_df.label.values
    timestamps = graph_df.ts.values

    random.seed(2020)

    train_mask = timestamps <= val_time if use_validation else timestamps <= test_time
    test_mask = timestamps > test_time
    val_mask = np.logical_and(timestamps <= test_time, timestamps > val_time) if use_validation else test_mask

    full_data = Data(sources, destinations, timestamps, edge_idxs, labels)

    train_data = Data(sources[train_mask], destinations[train_mask], timestamps[train_mask],
                      edge_idxs[train_mask], labels[train_mask])

    val_data = Data(sources[val_mask], destinations[val_mask], timestamps[val_mask],
                    edge_idxs[val_mask], labels[val_mask])

    test_data = Data(sources[test_mask], destinations[test_mask], timestamps[test_mask],
                     edge_idxs[test_mask], labels[test_mask])

    return full_data, node_features, edge_features, train_data, val_data, test_data




def get_data(dataset_name, val_ratio, test_ratio, different_new_nodes_between_val_and_test=False,
             randomize_features=False, max_normalization=False, logarithmize_weights=False,
             node_out_normalization=False, node_in_normalization=False, fill_all_edges=False,
             only_positive_edges=False):
    ### Load data and train val test split
    graph_df = pd.read_csv('./data/ml_{}.csv'.format(dataset_name))
    edge_features = np.load('./data/ml_{}.npy'.format(dataset_name))
    node_features = np.load('./data/ml_{}_node.npy'.format(dataset_name))
    # print(edge_features)
    # additional for CAW data specifically
    if dataset_name in ['enron', 'socialevolve', 'uci']:
        node_zero_padding = np.zeros((node_features.shape[0], 172 - node_features.shape[1]))
        node_features = np.concatenate([node_features, node_zero_padding], axis=1)
        edge_zero_padding = np.zeros((edge_features.shape[0], 172 - edge_features.shape[1]))
        edge_features = np.concatenate([edge_features, edge_zero_padding], axis=1)

    if randomize_features:
        node_features = np.random.rand(node_features.shape[0], node_features.shape[1])

    val_time, test_time = list(np.quantile(graph_df.ts, [(1 - val_ratio - test_ratio), (1 - test_ratio)]))

    graph_df['weight'] = edge_features[1:]

    # Whether we only keep the positive edges
    if only_positive_edges:
        graph_df = graph_df[graph_df.weight != 0]
        graph_df['idx'] = range(1, len(graph_df)+1)

    print(graph_df.dtypes)
    # Whether to have a fully connected graph with not existing edges an weight 0
    if fill_all_edges:
        all_edges_df = pd.DataFrame(columns=graph_df.columns)
        print(graph_df)
        unique_timestamps = graph_df.ts.unique()
        for t in tqdm(unique_timestamps):
            unique_sources = pd.unique(graph_df['u'])
            unique_destinations = pd.unique(graph_df['i'])
            unique_nodes = np.union1d(unique_sources, unique_destinations)
            edges = [[x, y, t, 0] for x in unique_nodes for y in unique_nodes]
            df = pd.DataFrame(edges, columns=['u', 'i', 'ts', 'weight'])
            all_edges_df = pd.concat([all_edges_df, df], ignore_index=True)

        merged = pd.merge(all_edges_df, graph_df, on=['u', 'i', 'ts'], how='left')

        # fill NaN values in 'w_x' with corresponding values in 'w_y'
        merged['weight_x'] = merged['weight_y'].fillna(merged['weight_x'])

        all_edges_df = merged[['u', 'i', 'ts', 'weight_x']].rename(columns={'weight_x': 'weight'})
        all_edges_df['label'] = [0 for _ in range(len(all_edges_df))]
        all_edges_df['idx'] = range(1, len(all_edges_df)+1)
        graph_df = all_edges_df.astype('int32')

    sources = graph_df.u.values
    destinations = graph_df.i.values
    edge_idxs = graph_df.idx.values
    labels = graph_df.label.values
    timestamps = graph_df.ts.values
    edge_features = graph_df.weight.values.reshape(-1,1)

    # normalisation
    if max_normalization:
        scaler = MinMaxScaler(feature_range=(0, 10))
        edge_features = scaler.fit_transform(edge_features)

    # logarithmize weights
    if logarithmize_weights:
        edge_features = np.log10(edge_features)
        # if after logarithm, the weight is too low, we set it to 0.001.
        edge_features = np.maximum(edge_features, 0.001)
    
    # for a given source node, divide all edges weights by the max edge weight that node has in a timestamp
    if node_out_normalization:
        print("Using node_out_normalization...")
        unique_timestamps = graph_df.ts.unique()
        for t in tqdm(unique_timestamps):
            unique_source = graph_df[graph_df.ts == t].u.unique()
            for x in unique_source:
                edges = graph_df[(graph_df.u == x) & (graph_df.ts == t)]
                # Calculate the max weight for these edges
                weight_sum = edges['weight'].sum()
                if weight_sum!=0:
                    # Divide all edge weights by the max weight
                    graph_df.loc[(graph_df.u == x) & (graph_df.ts == t), 'weight'] = graph_df['weight'] / weight_sum
        edge_features = graph_df.weight.values
        edge_features = edge_features.reshape(-1, 1)

    # for a given destination node, divide all edges weights by the max edge weight that node has in a timestamp
    if node_in_normalization:
        print("Using node_in_normalization...")
        unique_timestamps = graph_df.ts.unique()
        for t in unique_timestamps:
            unique_des = graph_df[graph_df.ts == t].i.unique()
            for x in unique_des:
                edges = graph_df[(graph_df.i == x) & (graph_df.ts == t)]
                # Calculate the max weight for these edges
                weight_sum = edges['weight'].sum()
                if weight_sum!=0:
                    # Divide all edge weights by the max weight
                    graph_df.loc[(graph_df.i == x) & (graph_df.ts == t), 'weight'] = graph_df['weight'] / weight_sum
        edge_features = graph_df.weight.values
        edge_features = edge_features.reshape(-1, 1)

    full_data = Data(sources, destinations, timestamps, edge_idxs, labels, edge_features)

    random.seed(2020)

    node_set = set(sources) | set(destinations)
    n_total_unique_nodes = len(node_set)

    # Compute nodes which appear at test time
    test_node_set = set(sources[timestamps > val_time]).union(
        set(destinations[timestamps > val_time]))
    # Sample nodes which we keep as new nodes (to test inductiveness), so than we have to remove all
    # their edges from training
    new_test_node_set = set(random.sample(test_node_set, int(0.1 * n_total_unique_nodes)))

    # Mask saying for each source and destination whether they are new test nodes
    new_test_source_mask = graph_df.u.map(lambda x: x in new_test_node_set).values
    new_test_destination_mask = graph_df.i.map(lambda x: x in new_test_node_set).values

    # Mask which is true for edges with both destination and source not being new test nodes (because
    # we want to remove all edges involving any new test node)
    observed_edges_mask = np.logical_and(~new_test_source_mask, ~new_test_destination_mask)

    # For train we keep edges happening before the validation time which do not involve any new node
    # used for inductiveness
    train_mask = np.logical_and(timestamps <= val_time, observed_edges_mask)

    train_data = Data(sources[train_mask], destinations[train_mask], timestamps[train_mask],
                      edge_idxs[train_mask], labels[train_mask], edge_features[train_mask])

    # define the new nodes sets for testing inductiveness of the model
    train_node_set = set(train_data.sources).union(train_data.destinations)
    assert len(train_node_set & new_test_node_set) == 0
    new_node_set = node_set - train_node_set

    val_mask = np.logical_and(timestamps <= test_time, timestamps > val_time)
    test_mask = timestamps > test_time

    if different_new_nodes_between_val_and_test:
        n_new_nodes = len(new_test_node_set) // 2
        val_new_node_set = set(list(new_test_node_set)[:n_new_nodes])
        test_new_node_set = set(list(new_test_node_set)[n_new_nodes:])

        edge_contains_new_val_node_mask = np.array(
            [(a in val_new_node_set or b in val_new_node_set) for a, b in zip(sources, destinations)])
        edge_contains_new_test_node_mask = np.array(
            [(a in test_new_node_set or b in test_new_node_set) for a, b in zip(sources, destinations)])
        new_node_val_mask = np.logical_and(val_mask, edge_contains_new_val_node_mask)
        new_node_test_mask = np.logical_and(test_mask, edge_contains_new_test_node_mask)


    else:
        edge_contains_new_node_mask = np.array(
            [(a in new_node_set or b in new_node_set) for a, b in zip(sources, destinations)])
        new_node_val_mask = np.logical_and(val_mask, edge_contains_new_node_mask)
        new_node_test_mask = np.logical_and(test_mask, edge_contains_new_node_mask)

    # validation and test with all edges
    val_data = Data(sources[val_mask], destinations[val_mask], timestamps[val_mask],
                    edge_idxs[val_mask], labels[val_mask], edge_features[val_mask])

    test_data = Data(sources[test_mask], destinations[test_mask], timestamps[test_mask],
                     edge_idxs[test_mask], labels[test_mask], edge_features[test_mask])

    # validation and test with edges that at least has one new node (not in training set)
    new_node_val_data = Data(sources[new_node_val_mask], destinations[new_node_val_mask],
                             timestamps[new_node_val_mask],
                             edge_idxs[new_node_val_mask], labels[new_node_val_mask], edge_features[new_node_val_mask])

    new_node_test_data = Data(sources[new_node_test_mask], destinations[new_node_test_mask],
                              timestamps[new_node_test_mask], edge_idxs[new_node_test_mask],
                              labels[new_node_test_mask], edge_features[new_node_test_mask])

    print("The dataset has {} interactions, involving {} different nodes".format(full_data.n_interactions,
                                                                                 full_data.n_unique_nodes))
    print("The training dataset has {} interactions, involving {} different nodes".format(
        train_data.n_interactions, train_data.n_unique_nodes))
    print("The validation dataset has {} interactions, involving {} different nodes".format(
        val_data.n_interactions, val_data.n_unique_nodes))
    print("The test dataset has {} interactions, involving {} different nodes".format(
        test_data.n_interactions, test_data.n_unique_nodes))
    print("The new node validation dataset has {} interactions, involving {} different nodes".format(
        new_node_val_data.n_interactions, new_node_val_data.n_unique_nodes))
    print("The new node test dataset has {} interactions, involving {} different nodes".format(
        new_node_test_data.n_interactions, new_node_test_data.n_unique_nodes))
    print("{} nodes were used for the inductive testing, i.e. are never seen during training".format(
        len(new_test_node_set)))

    return node_features, edge_features, full_data, train_data, val_data, test_data, \
           new_node_val_data, new_node_test_data


def compute_time_statistics(sources, destinations, timestamps):
    last_timestamp_sources = dict()
    last_timestamp_dst = dict()
    all_timediffs_src = []
    all_timediffs_dst = []
    for k in range(len(sources)):
        source_id = sources[k]
        dest_id = destinations[k]
        c_timestamp = timestamps[k]
        if source_id not in last_timestamp_sources.keys():
            last_timestamp_sources[source_id] = 0
        if dest_id not in last_timestamp_dst.keys():
            last_timestamp_dst[dest_id] = 0
        all_timediffs_src.append(c_timestamp - last_timestamp_sources[source_id])
        all_timediffs_dst.append(c_timestamp - last_timestamp_dst[dest_id])
        last_timestamp_sources[source_id] = c_timestamp
        last_timestamp_dst[dest_id] = c_timestamp
    assert len(all_timediffs_src) == len(sources)
    assert len(all_timediffs_dst) == len(sources)
    mean_time_shift_src = np.mean(all_timediffs_src)
    std_time_shift_src = np.std(all_timediffs_src)
    mean_time_shift_dst = np.mean(all_timediffs_dst)
    std_time_shift_dst = np.std(all_timediffs_dst)

    return mean_time_shift_src, std_time_shift_src, mean_time_shift_dst, std_time_shift_dst
