import pandas as pd
import itertools
import random
from collections import defaultdict, Counter

# Fixed group names (trees) - reused across iterations.
GROUP_NAMES = ['cedar', 'cypress', 'spruce', 'pine', 'fir', 'oak', 'maple', 'birch', 'ash', 'elm', 'chestnut']

def read_roster(filename):
    """Read the CSV file into a DataFrame with the appropriate encoding and drop extraneous unnamed columns."""
    df = pd.read_csv(filename, encoding='utf-8')  # or try 'cp1252'
    # Drop columns that start with "Unnamed"
    df = df.loc[:, ~df.columns.str.startswith('Unnamed')]
    return df

def get_next_iteration_column(df):
    """
    Find the first iteration column that has no group names assigned yet—
    only NaN or 'x' are allowed. If none is found, create a new iteration column.
    """
    # Identify columns that start with 'Iteration'
    iteration_cols = [col for col in df.columns[2:] if col.startswith('Iteration')]
    
    # Sort them in numerical order (Iteration 1, Iteration 2, etc.)
    # in case they are out of order
    def get_iter_num(c):
        try:
            return int(c.split()[1])
        except:
            return 999999  # fallback if column name is unusual
    
    iteration_cols.sort(key=get_iter_num)
    
    for col in iteration_cols:
        # Get non-null values in this column
        non_null_vals = df[col].dropna().unique()
        
        # If every non-null value is 'x', that means no group names have been assigned
        # so we can use it as the next iteration
        if all(val == 'x' for val in non_null_vals):
            return col
    
    # If no suitable column is found, create a new one
    if iteration_cols:
        highest_num = max(get_iter_num(c) for c in iteration_cols)
        new_iter_num = highest_num + 1
    else:
        new_iter_num = 1
    
    new_col = f"Iteration {new_iter_num}"
    df[new_col] = pd.NA
    return new_col

def extract_absences_and_present(df, iter_col):
    """Determine which students are absent in the current iteration.
    We assume that an 'x' in the iteration column marks an absence.
    Returns a tuple (present_students, absent_students) where each is a DataFrame slice."""
    absent_mask = df[iter_col] == 'x'
    present_mask = ~absent_mask
    present_df = df[present_mask].copy()
    absent_df = df[absent_mask].copy()
    return present_df, absent_df

def compute_past_pairings(df):
    """
    Build a dictionary with key as a frozenset of two roster numbers and value as
    the number of times they have been in the same group in previous iterations.
    """
    pairings = defaultdict(int)
    # Iterate over all grouping columns (skip roster number and name)
    for col in df.columns[2:]:
        # Skip the absence marker columns (if the entire column is "x" or similar, ignore)
        if df[col].dropna().isin(['x']).all():
            continue
        # For each group in the column, gather the students
        groups = df[col].dropna().unique()
        for group in groups:
            # Get students in this group for this iteration
            students_in_group = df[df[col] == group]['Roster'].tolist()
            # If the CSV does not have "Roster" column name, assume first column is roster number.
            for pair in itertools.combinations(students_in_group, 2):
                pairings[frozenset(pair)] += 1
    return pairings

def initial_group_structure(num_students):
    """
    Given the number of present students, find a grouping into groups of 3 and 4 
    such that 3x + 4y = num_students, with y minimized.
    Returns a list of group sizes (e.g., [3, 3, 4]).
    If no valid grouping exists (for n in {1, 2, 4, 5}), returns an empty list.
    """
    # Try y from 0 up to the maximum possible number of groups of 4.
    for y in range(0, num_students // 4 + 1):
        remaining = num_students - 4 * y
        if remaining % 3 == 0:
            x = remaining // 3
            # Create a list with x groups of 3 and y groups of 4.
            sizes = [3] * x + [4] * y
            return sizes
    return []

def grouping_conflict_score(group, past_pairings):
    """
    For a given group (list of roster numbers), calculate a conflict score.
    Each pair that has been grouped before contributes its count to the score.
    """
    score = 0
    for a, b in itertools.combinations(group, 2):
        score += past_pairings.get(frozenset((a, b)), 0)
    return score

def assign_groups(present_students, past_pairings, max_attempts=1000):
    """
    Attempt to assign groups to present students while minimizing repeat pairings.
    Uses a random shuffle based approach.
    Returns a tuple (best_assignment, best_total_score).
      - best_assignment is a list of groups (each group is a list of roster numbers).
      - best_total_score is the sum of conflict scores for the assignment.
    """
    students = present_students['Roster'].tolist()
    n = len(students)
    best_assignment = None
    best_score = float('inf')
    ideal_sizes = initial_group_structure(n)
    
    if not ideal_sizes or sum(ideal_sizes) != n:
        # If initial grouping is impossible (e.g., n=1,2,4,5)
        return None, None
    
    # Try multiple attempts to minimize conflict scores.
    for attempt in range(max_attempts):
        random.shuffle(students)
        assignment = []
        start = 0
        valid = True
        # Form groups according to ideal_sizes order.
        for size in ideal_sizes:
            if start + size <= n:
                group = students[start:start+size]
                assignment.append(group)
                start += size
            else:
                valid = False
                break
        if not valid:
            continue
        
        # Calculate the total conflict score for this assignment.
        total_score = sum(grouping_conflict_score(group, past_pairings) for group in assignment)
        if total_score < best_score:
            best_assignment = assignment
            best_score = total_score
            if best_score == 0:  # perfect grouping achieved
                break
    return best_assignment, best_score

def assign_group_names(assignment):
    """
    Given an assignment (list of groups), assign each group a name from GROUP_NAMES.
    Returns a dictionary mapping roster number to group name.
    """
    name_mapping = {}
    for i, group in enumerate(assignment):
        group_name = GROUP_NAMES[i % len(GROUP_NAMES)]
        for roster in group:
            name_mapping[roster] = group_name
    return name_mapping

def update_csv_with_assignment(filename, new_assignment, conflict_score, absent_students):
    """
    Update the CSV file with the new assignment:
      - Append a new column for the new iteration with the group names for present students.
      - Log conflicts in a row below if conflict_score > 0.
    """
    df = pd.read_csv(filename)
    next_col = get_next_iteration_column(df)
    
    # Create a mapping from roster to group name for present students.
    name_mapping = assign_group_names(new_assignment) if new_assignment is not None else {}
    
    # For each student in df, update the new iteration column:
    def assign_value(row):
        roster = row['Roster']
        # Explicitly check if the student is absent
        if roster in absent_students['Roster'].values:
            return 'x'  # Ensure absent students are always marked
        return name_mapping.get(roster, pd.NA)
    
    df[next_col] = df.apply(assign_value, axis=1)
    
    # Display conflict log in the terminal instead of appending it to the CSV
    if conflict_score and conflict_score > 0:
        print("\nConflict Log for this iteration:")
        print(f"Total conflict score: {conflict_score}")

    # Save the updated DataFrame without appending the conflict log
    df.to_csv(filename, index=False)

    
    # Save the updated CSV
    df.to_csv(filename, index=False, encoding='utf-8-sig')
    print(f"Updated CSV saved to {filename}.")

def main():
    filename = "roster.csv"  # replace with your CSV file name
    df = read_roster(filename)
    
    # Ensure the first column is named 'Roster' and second 'Name'
    if 'Roster' not in df.columns or 'Name' not in df.columns:
        df.columns = ['Roster', 'Name'] + list(df.columns[2:])
    
    next_iter = get_next_iteration_column(df)

    print("Full DataFrame contents before filtering absences:")	# Debugging
    print(df)							# Debugging

    present_df, absent_df = extract_absences_and_present(df, next_iter)
    
    # If no students are present, exit.
    if present_df.empty:
        print("No students present for this session.")
        return

    print("Absent students detected:")  # Debugging
    print(absent_df)			# Debugging

    past_pairings = compute_past_pairings(df)
    
    assignment, conflict_score = assign_groups(present_df, past_pairings)
    if assignment is None:
        print("Grouping is impossible for the number of present students.")
        return
    
    # Print assignment details (optional)
    print("Group Assignment for this iteration:")
    for group in assignment:
        print(group, "with conflict score:", grouping_conflict_score(group, past_pairings))
    print("Total conflict score for this iteration:", conflict_score)
    
    # Update the CSV with the new assignment and log conflicts if any.
    update_csv_with_assignment(filename, assignment, conflict_score, absent_df)

if __name__ == "__main__":
    main()
