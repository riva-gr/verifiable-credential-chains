import numpy as np
import csv
import copy
import networkx as nx
import time
import sys


percentage_of_elements = (
    60
)


score_thresholds = [0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 0.9]
experiment = 0
similarity_threshold = 0.4


if len(sys.argv) == 5:
    percentage_of_elements = int(sys.argv[1])
    score_thresholds = [float(v) for v in sys.argv[2].split(',')]
    experiment = int(sys.argv[3])
    similarity_threshold = float(sys.argv[4])


data_dir = "GT_and_CSV_files"
num_of_file = '_(' + str(experiment) + ')'
file_name_csv = data_dir + "/crs" + str(percentage_of_elements) + num_of_file + ".csv"
file_name_gt  = data_dir + "/ground_truth_sequences.csv"


def jaccard_similarity(set1, set2):

    intersection = set1.intersection(set2)
    union = set1.union(set2)
    if len(union) != 0:
        similarity = len(intersection) / len(union)
        return similarity
    return 0


def findCorrespondingGTseq(seq, gt_sequences):

    max_common_count = 0
    most_common_sublist = []
    for sublist in gt_sequences:
        common_count = len(
            set(seq) & set(sublist)
        )
        if common_count > max_common_count:
            max_common_count = common_count
            most_common_sublist = sublist
    return most_common_sublist


if __name__ == "__main__":

    data = []
    try:
        with open(file_name_csv, "r") as file:
            reader = csv.reader(file)
            for row in reader:
                if row:
                    data.append(row)
    except FileNotFoundError:
        print("The file ", file_name_csv, " does not exist!")
        sys.exit()


    data_labels = []
    for row in data:
        for element in row:
            if element not in data_labels:
                data_labels.append(element)
    data_labels.sort()
    num_of_labels = len(data_labels)


    ground_truth_sequences = []
    try:
        with open(file_name_gt, "r") as file:
            reader = csv.reader(file)
            for row in reader:
                if row:
                    ground_truth_sequences.append(row)
    except FileNotFoundError:
        print("The file ", file_name_gt, " does not exist!")


    start_time = time.time()


    num_of_nodes = len(data)
    similarities = np.zeros((num_of_nodes, num_of_nodes))


    for i in range(num_of_nodes):
        row = set(data[i])
        for j in range(i + 1, num_of_nodes):
            next_row = set(data[j])
            sim = jaccard_similarity(row, next_row)
            similarities[i][j] = sim


    graph = nx.Graph()


    for num_of_node, lbls_of_node in enumerate(data):
        graph.add_node(num_of_node, labels=lbls_of_node)


    for i in range(num_of_nodes):
        for j in range(i + 1, num_of_nodes):
            weight = similarities[i][j]
            if weight >= similarity_threshold:
                graph.add_edge(i, j, weight=weight)


    isolated_nodes = list(nx.isolates(graph))
    graph.remove_nodes_from(isolated_nodes)


    statistics_of = {
        node: np.empty((num_of_labels, 0), dtype=int) for node in graph.nodes()
    }


    labels_of = {node: set(graph.nodes[node]["labels"]) for node in graph.nodes()}


    initial_labels_of = copy.deepcopy(labels_of)


    label_counts = {}

    while True:

        labels_updated = False


        new_labels_for = {}


        column_of = {}

        for node in graph.nodes():

            for label in data_labels:
                label_counts[label] = 0


            current_node_labels = labels_of[node]


            new_labels_for[node] = set()


            for neighbor in graph.neighbors(node):

                neighbor_labels = labels_of[neighbor]


                for label in neighbor_labels:
                    label_counts[label] += 1


                new_labels = neighbor_labels - current_node_labels

                if new_labels:

                    labels_updated = True


                    new_labels_for[node].update(new_labels)


            column_of[node] = [label_counts[label] for label in data_labels]


        if labels_updated:
            for node in graph.nodes():
                statistics_of[node] = np.c_[statistics_of[node], column_of[node]]


        for node in graph.nodes():
            labels_of[node].update(new_labels_for[node])


        if not labels_updated:
            break


    final_stats_of = {}
    for node in graph.nodes():
        node_stats = {}
        for i, row in enumerate(statistics_of[node]):
            label = data_labels[i]
            if label not in initial_labels_of[node]:
                node_stats[label] = row
        final_stats_of[node] = node_stats


    score_of = {}
    for node in graph.nodes():
        degree = graph.degree(node)
        node_scores = {}
        for label, list_of_counts in final_stats_of[
            node
        ].items():
            weighted_sum = 0
            max_sum = 0
            for i in range(len(list_of_counts)):
                max_sum = max_sum + 1 / (i + 1)
                weighted_sum = weighted_sum + list_of_counts[i] / (degree * (i + 1))
            weighted_sum = weighted_sum / max_sum if max_sum != 0 else 0
            node_scores[label] = weighted_sum
        score_of[node] = node_scores


    shared_duration = time.time() - start_time


    for score_threshold in score_thresholds:
        t_add_labels = time.time()


        final_labels_of = copy.deepcopy(
            initial_labels_of
        )
        added_labels_of = {}


        for node in graph.nodes():
            added_labels_of[node] = set()
            for label in final_stats_of[node]:
                if (
                    score_of[node][label] > score_threshold
                ):
                    final_labels_of[node].add(label)
                    added_labels_of[node].add(label)

        duration = shared_duration + (time.time() - t_add_labels)


        sum1 = 0
        sum2 = 0


        for node in range(len(data)):
            init_labels = initial_labels_of.get(node, set(data[node]))
            final_labels = final_labels_of.get(node, init_labels)
            gt_corresponding = findCorrespondingGTseq(init_labels, ground_truth_sequences)
            intersection = set(final_labels) & set(gt_corresponding)

            sum1 += len(gt_corresponding)
            sum2 += len(intersection)
        coverage = sum2 / sum1 if sum1 > 0 else 0


        FN = (
            sum1 - sum2
        )
        TP = 0
        FP = 0

        for node in range(len(data)):
            init_labels = initial_labels_of.get(node, set(data[node]))
            gt_corresponding = findCorrespondingGTseq(init_labels, ground_truth_sequences)
            for label in added_labels_of.get(node, set()):
                if label in gt_corresponding:
                    TP += 1
                else:
                    FP += 1


        accuracy = (
            TP / (TP + FP + FN) if (TP + FP + FN) > 0 else 0
        )
        precision = (
            TP / (TP + FP) if (TP + FP) > 0 else 0
        )
        recall = (
            TP / (TP + FN) if (TP + FN) > 0 else 0
        )
        f1 = (
            2 * (precision * recall) / (precision + recall) if (precision + recall) > 0 else 0
        )


        print("\n\n_________________________________________________________\n\nMetrics: ")
        print(f" Score threshold: {score_threshold}")
        print(f" Running time: {duration:.3f}")
        print(f" Coverage: {coverage:.4f}")
        print(f" Accuracy: {accuracy:.4f}")
        print(f" Precision: {precision:.4f}")
        print(f" Recall: {recall:.4f}")
        print(f" F1 score: {f1:.4f}")


    print("\n\nexiting...")
