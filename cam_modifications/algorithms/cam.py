import os
os.system('clear')
import csv
import numpy as np
import time
import sys


write_results_to_file = False

min_support = 0.02
risup = 1.0
experiment = 0
percentage_of_elements = 100


if len(sys.argv) == 5:
    min_support = float(sys.argv[1])
    risup = float(sys.argv[2])
    experiment = int(sys.argv[3])
    percentage_of_elements = int(sys.argv[4])


data_dir = "GT_and_CSV_files_noise20"
num_of_file = '_(' + str(experiment) + ')'
file_name_csv = data_dir + "/crs" + str(percentage_of_elements) + num_of_file + ".csv"
file_name_gt  = data_dir + "/ground_truth_sequences.csv"


def generateLargerChains(list_of_chains):
    groups = {}
    for chain in list_of_chains:
        if chain[0] not in groups:
            groups[chain[0]] = []
        groups[chain[0]].append(chain)

    results = []
    for chain in list_of_chains:
        stack = [chain]
        while stack:
            current_chain = stack.pop()
            last_element = current_chain[-1]
            next_chains = groups.get(last_element, [])


            admissible = [nc for nc in next_chains
                          if not (set(nc[1:]) & set(current_chain))]

            if not admissible:
                if current_chain not in results:
                    results.append(current_chain)
                continue

            for next_chain in admissible:
                merged = current_chain + next_chain[1:]
                stack.append(merged)
    return results


def isSubsequence(subseq, seq):
    iter_seq = iter(seq)
    return all(item in iter_seq for item in subseq)


def removeSubsequences(list_os_lists):
    list_os_lists.sort(key=len)
    to_remove = set()
    for i in range(len(list_os_lists)):
        for j in range(i+1, len(list_os_lists)):
            if isSubsequence(list_os_lists[i], list_os_lists[j]):
                to_remove.add(tuple(list_os_lists[i]))
                break
    return [list(item) for item in list_os_lists if tuple(item) not in to_remove]


def findCorrespondingGTseq(chain, gt_sequences):
    max_common_count = 0
    most_common_sublist = []
    for sublist in gt_sequences:
        common_count = len(set(chain) & set(sublist))
        if common_count > max_common_count:
            max_common_count = common_count
            most_common_sublist = sublist
    return most_common_sublist


def calculatePrecision(predicted, ground_truth):
    gt_set = set(ground_truth)
    predicted_set = set(predicted)
    TP = predicted_set & gt_set
    precision = len(TP) / len(predicted_set) if predicted_set else 0
    return precision


def calculateRecall(predicted, ground_truth):
    gt_set = set(ground_truth)
    predicted_set = set(predicted)
    TP = predicted_set & gt_set
    recall = len(TP) / len(gt_set) if gt_set else 0
    return recall


def calculateAccuracy(predicted, ground_truth):
    gt_set = set(ground_truth)
    predicted_set = set(predicted)
    TP = predicted_set.intersection(gt_set)
    total_elements = len(predicted_set | gt_set)
    accuracy = len(TP) / total_elements if total_elements else 0
    return accuracy


if __name__ == "__main__":
    dataset = []
    num_of_rows = 0
    try:
        with open(file_name_csv, 'r') as file:
            reader = csv.reader(file)
            for row in reader:
                if row:
                    dataset.append(row)
                    num_of_rows += 1
    except FileNotFoundError:
        print("The file ", file_name_csv, " does not exist!")
        sys.exit()


    creds = []
    for row in dataset:
        for element in row:
            if element not in creds:
                creds.append(element)
    creds.sort()


    ground_truth_sequences = []
    try:
        with open(file_name_gt, 'r') as file:
            reader = csv.reader(file)
            for row in reader:
                if row:
                    ground_truth_sequences.append(row)
    except FileNotFoundError:
        print("The file ", file_name_gt, " does not exist!")


    start_time = time.time()


    counts = np.zeros((len(creds), len(creds)), dtype=int)


    index_of = {cred: k for k, cred in enumerate(creds)}
    for row in dataset:
        position = {}
        for pos, element in enumerate(row):
            if element not in position:
                position[element] = pos
        elements = list(position.keys())
        for a in range(len(elements)):
            for b in range(len(elements)):
                if position[elements[a]] < position[elements[b]]:
                    counts[index_of[elements[a]]][index_of[elements[b]]] += 1


    links = []
    percentages = []

    for i in range(0, len(counts)):
        for j in range(0, len(counts)):
            s = counts[j][i] + counts[i][j]
            if s != 0 and s >= num_of_rows * min_support:
                if (counts[i][j] / s) >= risup:
                    temp_list = [creds[i], creds[j]]
                    percentages.append((counts[i][j] / s))
                    links.append(temp_list)


    chains = generateLargerChains(links)
    chains = removeSubsequences(chains)

    duration = time.time() - start_time


    print("\n\nPredicted chains:\n")
    for chain in chains:
        print(chain)


    if chains:
        print("\n\n____________________________________________________________________")
        print("\nComparison between predicted chains and their corresponding ground truth sequences:")

        sum_accuracy = 0
        sum_precision = 0
        sum_recall = 0
        sum_corr_lengths = 0
        sum_inter_lengths = 0

        for count, chain in enumerate(chains, start=1):
            corresponding = findCorrespondingGTseq(chain, ground_truth_sequences)
            intersection = set(chain) & set(corresponding)


            sum_inter_lengths += len(intersection)
            sum_corr_lengths += len(corresponding)

            accuracy = calculateAccuracy(chain, corresponding)
            sum_accuracy += accuracy

            precision = calculatePrecision(chain, corresponding)
            sum_precision += precision

            recall = calculateRecall(chain, corresponding)
            sum_recall += recall

            f1 = 2 * (precision * recall) / (precision + recall) if (precision + recall) > 0 else 0

            print(f"\nPredicted: {chain}, \nGrounth truth corresponding: {corresponding}")
            print(f"Accuracy: {accuracy:.4f} Precision: {precision:.4f}, Recall: {recall:.4f}, F1 score: {f1:.4f}")


        coverage = sum_inter_lengths / sum_corr_lengths if sum_corr_lengths else 0
        overall_accuracy = sum_accuracy / count
        overall_precision = sum_precision / count
        overall_recall = sum_recall / count
        f1 = 2 * (overall_precision * overall_recall) / (overall_precision + overall_recall) if (overall_precision + overall_recall) > 0 else 0
    else:
        overall_accuracy = overall_precision = overall_recall = f1 = coverage = 0


    print("\n\n_________________________________________________________\n\nMetrics: ")
    print(f" Running time: {duration:.3f}")
    print(f" Overall Coverage: {coverage:.4f}")
    print(f" Overall Accuracy: {overall_accuracy:.4f}")
    print(f" Overall Precision: {overall_precision:.4f}")
    print(f" Overall Recall: {overall_recall:.4f}")
    print(f" Overall F1 score: {f1:.4f}")


    formatted_risup = "{:.1f}".format(risup)


    if write_results_to_file:
        results_file_name = 'Results_original/CAM/min_support_' + str(min_support) + '/CAM_risup_' + formatted_risup + '.txt'
        os.makedirs(os.path.dirname(results_file_name), exist_ok=True)
        with open(results_file_name, 'a') as file:
            file.write(f"\n{percentage_of_elements}  {duration:.3f}  {coverage:.4f} {overall_accuracy:.4f} {overall_precision:.4f}  {overall_recall:.4f}  {f1:.4f}  ")
            if percentage_of_elements == 100:
                file.write(f"\n")


    print("\n\n\n\n\nexiting...")
