import subprocess
import pandas as pd
import plotly.figure_factory as ff
from datetime import datetime

def create_gantt_chart():
    # Get list of all pods
    get_pods_command = "kubectl get pods --no-headers -o custom-columns=NAME:.metadata.name"
    pods_output = subprocess.check_output(get_pods_command, shell=True).decode("utf-8")
    pod_names = pods_output.split("\n")[:-1]

    # Create DataFrame for storing pod names and start times
    df_list = []

    # counters for each type of pod
    atest_counter = 1
    nlc_counter = 1
    xnoise_counter = 1

    # Get start time for each pod and add it to the DataFrame
    for pod_name in pod_names:
        try:
            get_start_time_command = f"kubectl describe pod {pod_name} | grep 'Start Time:'"
            start_time_output = subprocess.check_output(get_start_time_command, shell=True).decode("utf-8")
            start_time_str = start_time_output.split(":")[1].strip()
            
            # print the start_time_str to check its format
            print(f"Start time for pod {pod_name}: {start_time_str}")
            
            start_time = datetime.strptime(start_time_str, "%a, %d %b %Y %H")  # Adjusted date format


            short_name = ""

            if pod_name.startswith("atest"):
                short_name = f"LC{atest_counter}"
                atest_counter += 1
            elif pod_name.startswith("ncl-"):
                short_name = f"NLC{nlc_counter}"
                nlc_counter += 1
            elif pod_name.startswith("xnoise"):
                short_name = f"extra{xnoise_counter}"
                xnoise_counter += 1

            # print the short_name to check its value
            print(f"Short name for pod {pod_name}: {short_name}")

            new_row = pd.DataFrame([{"Task": short_name, "Start": start_time, "Finish": datetime.now()}])  # Use the current time as the finish time
            df_list.append(new_row)
        except subprocess.CalledProcessError:
            print(f"Skipping pod {pod_name} as it is still pending...")
            continue

    # Concatenate all DataFrames
    df = pd.concat(df_list, ignore_index=True)

    # Convert to datetime
    df['Start'] = pd.to_datetime(df['Start'])
    df['Finish'] = pd.to_datetime(df['Finish'])

    # Create Gantt chart
    fig = ff.create_gantt(df, index_col='Task', show_colorbar=True, task_names='Task', group_tasks=True)

    # Update layout properties
    fig.update_layout(showlegend=False, autosize=True, title_text="")

    # Remove range slider
    fig.update_xaxes(rangeslider_visible=False)

    # Remove modebar buttons
    fig.update_layout(modebar=dict(orientation='v', bgcolor='rgba(0,0,0,0)'))

    # Save figure as png
    fig.write_image("gantt_chart.png")

if __name__ == "__main__":
    create_gantt_chart()
