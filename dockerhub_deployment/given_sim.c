#include <stdio.h>
#include <stdlib.h>
#include <stdbool.h>
#include <unistd.h>
#include <getopt.h>
#include <stdint.h>
#include <inttypes.h>
#include <time.h>
#include <math.h>
#include <sys/prctl.h>
#include <pthread.h>

#define MIN(a,b) (((a)<(b))?(a):(b))
#define MAX(a,b) (((a)>(b))?(a):(b))

//30ms
//#define MAX_LATENCY_US 30000
//#define HIST_RESOLUTION 10

//100ms
#define MAX_LATENCY_US 100000
#define HIST_RESOLUTION 100

//30s
//#define MAX_LATENCY_US 30000000
//#define HIST_RESOLUTION 10000
#define HIST_BUCKETS MAX_LATENCY_US/HIST_RESOLUTION
#define MAX_THREADS 50
#define S2NS 1000000000lu

// Define a struct to store the parameter values
struct params {
    int itterations;
    int sleep_time_us;
    int test_duration_s;
    int thread_count;
};

// Define struct for to define values for each thread
struct loadgen_args {
    uint64_t latency_hist[2][HIST_BUCKETS];
    uint64_t    duration_s;
    double      itt_avg;
    double      sleep_time_avg_us;
}; 

uint64_t latency_hist_aggregated[2][HIST_BUCKETS];

static long int get_seed() {
    struct timespec ts;
    clock_gettime(CLOCK_MONOTONIC, &ts);
    return ts.tv_nsec;
}

static inline uint64_t get_ns() {
    struct timespec ts;
    clock_gettime(CLOCK_MONOTONIC, &ts);
    return (((uint64_t)ts.tv_sec) * 1000000000lu + ts.tv_nsec);
}

static inline double ran_expo(struct drand48_data *rand_buffer_p, 
                              double lambda_inv) {
    double x;
    drand48_r(rand_buffer_p, &x);
    return -log(1.0 - x) * lambda_inv;
}

static inline uint64_t get_rand_itt(struct drand48_data *rand_buffer_p, 
                                    double itt_avg) {
    double itt_res;
    double itt;
    
    itt = ran_expo(rand_buffer_p, itt_avg);

    itt_res = MAX(2.0, itt);
    itt_res = MIN(10*itt_avg, itt_res);
    return (uint64_t) itt_res;
}

static void clear_hist_stat(struct loadgen_args *my_data) {
    int i;
    for (i = 0; i < HIST_BUCKETS;i++) {
        my_data->latency_hist[0][i] = 0;
        my_data->latency_hist[1][i] = 0;
    }
}

// Function to decode command line options and return the parameter values as a struct
static struct params decode_options(int argc, char *argv[]) {
    int option;
    struct params p = {10000, 600, 30, 2}; // Default values

    while ((option = getopt(argc, argv, "r:s:t:c:h")) != -1) {
        switch (option) {
            case 'r':
                p.itterations = atoi(optarg);
                break;
            case 's':
                p.sleep_time_us = atoi(optarg);
                break;
            case 't':
                p.test_duration_s = atoi(optarg);
                break;
            case 'c':
                p.thread_count = atoi(optarg);
                break;
            case 'h':
                printf("Usage: %s [options]\n", argv[0]);
                printf("Options:\n");
                printf("  -r <time>    Set loop itterations (default: 10000)\n");
                printf("  -s <time>    Set sleep time in microseconds (default: 600)\n");
                printf("  -t <time>    Set test duration in seconds (default: 30)\n");
                printf("  -c <count>   Set the number of threads to create (default: 2)\n");
                printf("  -h           Display this help message and exit\n");
                exit(EXIT_SUCCESS);
            default:
                printf("Invalid option\n");
                exit(EXIT_FAILURE);
        }
    }

    return p;
}

static void inline add_hist_stat(struct loadgen_args *my_data, 
                                 uint64_t curr_ts_ns, 
                                 uint64_t next_ts_ns, 
                                 uint64_t sched_latency_ns, 
                                 uint64_t sleep_time_us) {
    uint64_t latency_bin;
    if (next_ts_ns > curr_ts_ns) {
        printf("add_hist: error1\n");
    } else {
        //** record data in job_comp_time column based on diff between curr_ts and next_ts
        latency_bin = (curr_ts_ns - next_ts_ns)/(1000*HIST_RESOLUTION);
        if (latency_bin >= HIST_BUCKETS) {
            my_data->latency_hist[0][HIST_BUCKETS - 1] += 1;
        } else {
            my_data->latency_hist[0][latency_bin] += 1;
        }
    }
    if (sleep_time_us != 0) {
        //** record data in sched_delay column based on recorded latency after sleep
        latency_bin = sched_latency_ns/(1000*HIST_RESOLUTION);
        if (latency_bin >= HIST_BUCKETS) {
            my_data->latency_hist[1][HIST_BUCKETS - 1] += 1; 
        } else {
            my_data->latency_hist[1][latency_bin] += 1;
        }
    }
}

static void* thread(void* input) 
{
	uint64_t i, next_ts_ns, curr_ts_ns, itt, end_time_ns, sched_latency_ns, stat_start, stat_stop, job_start_ts, job_curr_ts;
	volatile uint64_t c;
	unsigned int sleep_time_us;
    struct loadgen_args *my_data = (struct loadgen_args*)input;
    volatile double itt_avg = (double) my_data->itt_avg;
	volatile double sleep_time_avg_us = (double) my_data->sleep_time_avg_us;

    struct drand48_data rand_buffer;
    srand48_r(get_seed(), &rand_buffer);
    prctl(PR_SET_TIMERSLACK, 1lu);

	curr_ts_ns  = get_ns();
	next_ts_ns  = curr_ts_ns;
    end_time_ns = next_ts_ns + my_data->duration_s*S2NS + 10*S2NS;
    sched_latency_ns = 0;
	stat_start = curr_ts_ns + 5*S2NS;
    stat_stop  = curr_ts_ns + 5*S2NS + my_data->duration_s*S2NS;
	
	for (;;) {
        if (curr_ts_ns > end_time_ns) 
            pthread_exit(NULL);

        //** SET curr_ts_ns (update) & record data
        curr_ts_ns = get_ns();
        if ((curr_ts_ns > stat_start) && (curr_ts_ns < stat_stop)) 
            add_hist_stat(my_data, curr_ts_ns, next_ts_ns, 
                          sched_latency_ns, sleep_time_us);

        //** SET next_ts based on random (this is when the thread should start working)
        next_ts_ns += (uint64_t) 1000*ran_expo(&rand_buffer, sleep_time_avg_us);
		
		if (next_ts_ns < curr_ts_ns) {
			sleep_time_us = 0;
		}
		else {
			sleep_time_us = (unsigned int) (next_ts_ns - curr_ts_ns)/1000;
            usleep(sleep_time_us);
		}

        if (sleep_time_us > 0)
            sched_latency_ns = get_ns() - (curr_ts_ns + 1000*sleep_time_us);
        else
            sched_latency_ns = 0;

        itt = get_rand_itt(&rand_buffer, itt_avg);
                       
        for (i=0; i < itt; i++) {
			c = i;
         };
	}
}


static void start_simulation_threads(struct params p) {
	pthread_t t[MAX_THREADS];
	struct loadgen_args thread_data[MAX_THREADS];
    int i, j;

	for (i = 0; i < p.thread_count; i++) {
        clear_hist_stat(&thread_data[i]);
        thread_data[i].duration_s = p.test_duration_s;
        thread_data[i].itt_avg = p.itterations;
        thread_data[i].sleep_time_avg_us = p.sleep_time_us;
	    pthread_create(&t[i],NULL,thread,(void*) &thread_data[i]); 		
	}

	for (i = 0; i < p.thread_count; i++) {
        pthread_join(t[i], NULL);
	    for (j=0; j < HIST_BUCKETS; j++) {
            latency_hist_aggregated[0][j] += thread_data[i].latency_hist[0][j];
            latency_hist_aggregated[1][j] += thread_data[i].latency_hist[1][j];
	    }
    }

}

static void print_stats() {
    int i;

    printf("%-10s %-10s %-10s\n", "Bin[us]", "Job_comp_time", "sched_delay");

    for (i=0; i < HIST_BUCKETS; i++) {

        printf("%-10d %-10d %-10d\n", i*HIST_RESOLUTION, 
               latency_hist_aggregated[0][i], 
               latency_hist_aggregated[1][i]);
    }
}

int main(int argc, char *argv[]) {
    struct params p = decode_options(argc, argv);

    fprintf(stderr,"sleep_time_us = %d\n", p.sleep_time_us);
    fprintf(stderr,"test_duration_s = %d\n", p.test_duration_s);
    fprintf(stderr,"thread_count = %d\n", p.thread_count);

    start_simulation_threads(p);

    print_stats();

    return 0;
}

