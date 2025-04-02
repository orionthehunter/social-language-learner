import pandas as pd
import numpy as np

def count_groupings(filename):
    df = pd.read_csv(filename)
    iterations = [col for col in df.columns if "Iteration" in col]
    
    # Extract names and initialize the matrix
    names = df["Name"].tolist()
    num_students = len(names)
    count_matrix = np.zeros((num_students, num_students), dtype=int)
    
    # Build a dictionary mapping names to indices
    name_to_index = {name: i for i, name in enumerate(names)}
    
    # Count occurrences of groupings
    for iteration in iterations:
        groups = df.groupby(iteration)["Name"].apply(list)
        for group in groups:
            for i in range(len(group)):
                for j in range(i + 1, len(group)):
                    idx1, idx2 = name_to_index[group[i]], name_to_index[group[j]]
                    count_matrix[idx1][idx2] += 1
                    count_matrix[idx2][idx1] += 1
    
    # Convert to DataFrame for readability
    count_df = pd.DataFrame(count_matrix, index=names, columns=names)
    return count_df

if __name__ == "__main__":
    filename = "roster.csv"  # Change to the actual filename
    result = count_groupings(filename)
    print("Group Pairing Frequency Matrix:")
    print(result)
