data_path=~/smore/data/FB15k
tasks="1p,2p,3p,2i,3i,ip,pi"
# step 0: (optional) generating test samples
if [ "$1" == "-gen" ]; then
    python generate_test.py -mr -t $tasks -p $data_path -n 100
fi

# test traditional rdf queries
python rdf_test.py -p $data_path -t $tasks

# test ngdbs
(
    cd ../smore/training/box_scripts/
    bash deploy_15k.sh
)

timestamp=$(date +"%Y-%m-%d_%H-%M-%S")
output_file="test_results_$timestamp.log"

python analyze_results.py -t $tasks -p $data_path --test_accuracy --test_time --test_hard_ans > "$output_file"