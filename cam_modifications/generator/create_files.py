import csv
import copy
import random
import os

os.system('clear')


NUM_MISC = 20
MIN_LENGTH = 2
MAX_LENGTH = 11
NUM_SEQ_PER_CHAIN = 100
NUM_REPLICATES = 5
BASE_SEED = 20260911

OUT_DIR = f"GT_and_CSV_files_noise{NUM_MISC}"


def createGroundTrusthSequences(min_length, max_length):
    dataset = []
    for length in range(min_length, max_length + 1):
        sublist = []
        letter = chr(65 + len(dataset))
        for i in range(1, length + 1):
            sublist.append(f"{letter}{i}")
        dataset.append(sublist)
    return dataset


def createInorderSequences(base_sequence, num_of_seq, threshold):
    sequences = []
    for _ in range(num_of_seq):
        temp = [item for item in base_sequence if random.random() < threshold]
        sequences.append(temp)
    return sequences


def combineSequences(seq1, seq2):
    combined = []
    copied_seq1 = copy.copy(seq1)
    copied_seq2 = copy.copy(seq2)
    while copied_seq1 or copied_seq2:
        chosen_seq = random.choice([copied_seq1, copied_seq2])
        if not chosen_seq:
            chosen_seq = copied_seq1 if chosen_seq is copied_seq2 else copied_seq2
        combined.append(chosen_seq.pop(0))
    return combined


def create_complementary_list(min_len, max_len, num_misc):
    length = random.randint(min_len, max_len)
    if length > num_misc:
        raise ValueError("The miscellaneous set is smaller than the number of labels to draw!")
    unique_numbers = random.sample(range(1, num_misc + 1), length)
    return ['cr' + str(num) for num in unique_numbers]


if __name__ == "__main__":
    os.makedirs(OUT_DIR, exist_ok=True)

    ground_truth_sequences = createGroundTrusthSequences(MIN_LENGTH, MAX_LENGTH)

    with open(os.path.join(OUT_DIR, 'ground_truth_sequences.csv'), 'w', newline='') as file:
        writer = csv.writer(file)
        for gt_seq in ground_truth_sequences:
            writer.writerow(gt_seq)

    num_gt_creds = sum(len(s) for s in ground_truth_sequences)

    for replicate in range(NUM_REPLICATES):
        for percentage in range(10, 110, 10):
            random.seed(BASE_SEED + replicate * 1000 + percentage)

            filename = os.path.join(OUT_DIR, f'crs{percentage}_({replicate}).csv')
            threshold = percentage / 100

            finalSequences = []
            for gt_seq in ground_truth_sequences:
                inorder = createInorderSequences(gt_seq, NUM_SEQ_PER_CHAIN, threshold)
                misc = [create_complementary_list(MIN_LENGTH, MAX_LENGTH, NUM_MISC)
                        for _ in range(NUM_SEQ_PER_CHAIN)]
                for k in range(NUM_SEQ_PER_CHAIN):
                    finalSequences.append(combineSequences(inorder[k], misc[k]))

            with open(filename, 'w', newline='') as file:
                writer = csv.writer(file)
                for s in finalSequences:
                    writer.writerow(s)

    print(f"\nGround truth : {len(ground_truth_sequences)} chains, lengths "
          f"{MIN_LENGTH}..{MAX_LENGTH}, {num_gt_creds} distinct credentials")
    print(f"Miscellaneous: {NUM_MISC} credentials (cr1..cr{NUM_MISC}), "
          f"{MIN_LENGTH}..{MAX_LENGTH} inserted per identity")
    print(f"Population   : {NUM_SEQ_PER_CHAIN * len(ground_truth_sequences)} identities per file")
    print(f"Files        : {NUM_REPLICATES} replicates x 10 percentages -> {OUT_DIR}/")
    print("\nExiting...")
