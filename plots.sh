# to run in the parent dir

# bulk experimental design
python3 plot_results.py --namefirsttest simple_fec_bulk_bbr --namesecondtest bbr -f results_db/bulk.db --filesize 10000,40000,100000,1000000,10000000 -m CDF --metric time --labelfirsttest "QUIC FEC" --labelsecondtest QUIC --transform ratio --xlabel '$\frac{DCT_{FlEC}}{DCT_{QUIC}}$' --ylabel 'CDF' --ylim 0,1.005 --yticks 0,1 --xlim 0.25,4 --xticks 0.25,0.5,0.75,1,1.33,2,4 --title '$bw \in [1, 30]Mbps$, $loss \in [0.1, 8]\%$, $RTT \in [10, 200]ms$' --labelfirsttest "QUIC-FEC" --labelsecondtest "QUIC" -t results_plots/bulk.pdf --log


python3 plot_results.py --namefirsttest simple_fec_ac_rlnc_bbr --namesecondtest bbr -f results_db/bulk.db --filesize 10000,40000,100000,1000000,10000000 -m CDF --metric time --labelfirsttest "QUIC FEC" --labelsecondtest QUIC --transform ratio --xlabel '$\frac{DCT_{FlEC}}{DCT_{QUIC}}$' --ylabel 'CDF' --ylim 0,1.005 --yticks 0,1 --xlim 0.25,4 --xticks 0.25,0.5,0.75,1,1.33,2,4 --title '$bw \in [1, 30]Mbps$, $loss \in [0.1, 8]\%$, $RTT \in [10, 200]ms$' --labelfirsttest "QUIC-FEC" --labelsecondtest "QUIC" -t results_plots/bulk_vs_ac_rlnc.pdf --log


# buffer-limited


# # using bbr instead of ideal cwin
python3 plot_results.py --namefirsttest simple_fec_causal_bbr --namesecondtest bbr --transform ratio -m CDF -f results_db/rwin_limited_experimental_design.db --metric time --filesize 5000000 --xlabel "$\frac{DCT_{FlEC}}{DCT_{QUIC}}$" --ylabel "CDF" --xlim 0.25,4 --xticks=0.25,0.5,0.75,1,1.33,2,4 --cdf-multiplex-metric stream_receive_window_size --cdf-multiplex-metric-in-bytes --log --title '$RTT \in [10, 400]ms$, $bw \in [1, 30]Mbps$, $loss \in [0.1, 3]\%$'  -t results_plots/rwin_limited_experimental_design.pdf


python3 boxplot_results.py --namefirsttest simple_fec_causal_bbr --namesecondtest bbr --transform ratio -m boxplot -f results_db/rwin_limited_loss_05.db --metric time --uni-x-metric stream_receive_window_size --filesize 5000000 --xlabel "receive window size (MB)" --no-legend --ylog --ylabel '$\frac{DCT_{FlEC}}{DCT_{QUIC}}$'  --title "RTT = 400ms, BW = 8Mbps, loss = 0.5\%"  --ylim 0.6,1.67 --yticks "0.75,0.9,1,1.11,1.33=0.75,0.9,,1.11,1.33" --xticks "70000,150000,250000,400000,1000000,3000000=0.07,0.15,0.25,0.4,1,3" -t results_plots/rwin_limited_loss_05.pdf

python3 boxplot_results.py --namefirsttest simple_fec_causal_bbr --namesecondtest bbr --transform ratio -m boxplot -f results_db/rwin_limited_loss_2.db --metric time --uni-x-metric stream_receive_window_size --filesize 5000000 --xlabel "receive window size (MB)" --no-legend --ylog --ylabel '$\frac{DCT_{FlEC}}{DCT_{QUIC}}$'  --title "RTT = 400ms, BW = 8Mbps, loss = 2\%"  --ylim 0.6,1.67 --yticks "0.75,0.9,1,1.11,1.33=0.75,0.9,,1.11,1.33" --xticks "70000,150000,250000,400000,1000000,3000000=0.07,0.15,0.25,0.4,1,3" -t results_plots/rwin_limited_loss_2.pdf


# bbr experimental design bursts

python3 plot_results.py --namefirsttest simple_fec_causal_bbr --namesecondtest bbr --transform ratio -m CDF -f results_db/rwin_limited_experimental_design_bursty.db --metric time --filesize 5000000 --xlabel "$\frac{DCT_{FlEC}}{DCT_{QUIC}}$" --ylabel "CDF" --xlim 0.5,2 --xticks 0.5,0.75,1,1.33,2 --cdf-multiplex-metric stream_receive_window_size --cdf-multiplex-metric-in-bytes --log --title '$RTT \in [10, 400]ms$, $bw \in [1, 30]Mbps$, $G_{\hat{p}} \in [0.1, 1.5]\%$' -t results_plots/rwin_limited_experimental_design_bursty.pdf


# time VS bytes tradeoff
python3 plot_results_bytes_time_tradeoff.py --namefirsttest simple_fec_causal_bbr --namesecondtest bbr -f results_db/rwin_limited_scatter_150kB.db --metric time --uni-x-metric server_bytes_sent_simple_fec_causal_bbr,server_bytes_sent_bbr --filesize 5000000 --xlabel "bytes overhead" --ylabel "DCT (ms)" --title "RTT = 400ms, BW = 8Mbps, loss = 2\%, rwin=150kB" --rwin-size 150000 --labelfirsttest FlEC --labelsecondtest QUIC --normalize-bytes-sent -t results_plots/rwin_limited_scatter_150kB.pdf

python3 plot_results_bytes_time_tradeoff.py --namefirsttest simple_fec_causal_bbr --namesecondtest bbr -f results_db/rwin_limited_scatter_6MB.db --metric time --uni-x-metric server_bytes_sent_simple_fec_causal_bbr,server_bytes_sent_bbr --filesize 5000000 --xlabel "bytes overhead" --ylabel "DCT (ms)" --title "RTT = 400ms, BW = 8Mbps, loss = 0.5\%, rwin=6MB" --rwin-size 6000000 --labelfirsttest FlEC --labelsecondtest QUIC --normalize-bytes-sent -t results_plots/rwin_limited_scatter_6MB.pdf --ylim 7000,8200 --yticks 7000,7500,8000



# messages

# bbr bytes sent
python3 plot_results.py --namefirsttest simple_fec_message_bbr,simple_fec_message_bbr_without_api --namesecondtest bbr,bbr -f results_db/messages_loss_1.db,results_db/messages_loss_1.db --filesize 5000000 -m uni --metric server_bytes_sent --labelfirsttest "FlEC" --labelsecondtest QUIC --transform ratio --xlabel "one-way delay (ms)" --ylabel 'byte sent $\frac{FlEC}{QUIC}$' --ylim 0.33,3 --ylog --yticks "0.33,0.5,0.9,1,1.1,2,3=0.33,0.5,0.9,,1.1,2,3" --xticks 5,25,50,75,100,125,150,175,200 --title '$bw$ = 8Mbps, $loss$ = 1\%, $deadline$ = 250ms' --labelfirsttest "FlEC" --labelsecondtest "QUIC" --legends '$FlEC_{API}$,$FlEC_{NO-API}$' -t results_plots/messages_loss_1_bytes_sent_with_and_without_api.pdf

# bbr 95pct
python3 plot_results.py --namefirsttest simple_fec_message_bbr --namesecondtest bbr -f results_db/messages_loss_1.db --filesize 5000000 -m uni --metric message_95_pct_delivery_delay --labelfirsttest "FlEC" --labelsecondtest QUIC --transform none --xlabel "one-way delay (ms)" --ylabel 'delivery time $95^{th} percentile$' --ylim 0,1000000 --yticks 50000,150000,250000,500000=50,150,250,500 --xticks 50,75,100,125,150,175,200 --title '$bw$ = 8Mbps, $loss$ = 1\%, $deadline$ = 250ms' --labelfirsttest "FlEC" --labelsecondtest "QUIC" -t results_plots/messages_loss_1_95_pct.pdf

# bbr 97pct
python3 plot_results.py --namefirsttest simple_fec_message_bbr --namesecondtest bbr -f results_db/messages_loss_1.db --filesize 5000000 -m uni --metric message_97_pct_delivery_delay --labelfirsttest "FlEC" --labelsecondtest QUIC --transform none --xlabel "one-way delay (ms)" --ylabel 'delivery time $97^{th} percentile$' --ylim 0,1000000 --yticks 50000,150000,250000,500000=50,150,250,500 --xticks 50,75,100,125,150,175,200 --title '$bw$ = 8Mbps, $loss$ = 1\%, $deadline$ = 250ms' --labelfirsttest "FlEC" --labelsecondtest "QUIC" -t results_plots/messages_loss_1_97_pct.pdf

# bbr 98pct
python3 plot_results.py --namefirsttest simple_fec_message_bbr --namesecondtest bbr -f results_db/messages_loss_1.db --filesize 5000000 -m uni --metric message_98_pct_delivery_delay --labelfirsttest "FlEC" --labelsecondtest QUIC --transform none --xlabel "one-way delay (ms)" --ylabel 'delivery time $98^{th} percentile$' --ylim 0,1000000 --yticks 50000,150000,250000,500000=50,150,250,500 --xticks 50,75,100,125,150,175,200 --title '$bw$ = 8Mbps, $loss$ = 1\%, $deadline$ = 250ms' --labelfirsttest "FlEC" --labelsecondtest "QUIC" -t results_plots/messages_loss_1_98_pct.pdf

# bbr 99pct
python3 plot_results.py --namefirsttest simple_fec_message_bbr --namesecondtest bbr -f results_db/messages_loss_1.db --filesize 5000000 -m uni --metric message_99_pct_delivery_delay --labelfirsttest "FlEC" --labelsecondtest QUIC --transform none --xlabel "one-way delay (ms)" --ylabel 'delivery time $99^{th} percentile$' --ylim 0,1000000 --yticks 50000,150000,250000,500000=50,150,250,500 --xticks 50,75,100,125,150,175,200 --title '$bw$ = 8Mbps, $loss$ = 1\%, $deadline$ = 250ms' --labelfirsttest "FlEC" --labelsecondtest "QUIC" -t results_plots/messages_loss_1_99_pct.pdf

# bbr long deliveries pct
python3 plot_results.py --namefirsttest simple_fec_message_bbr,simple_fec_message_bbr_without_api --namesecondtest bbr,bbr -f results_db/messages_loss_1.db,results_db/messages_loss_1.db --filesize 5000000 -m uni --metric message_long_deliveries_pct --labelfirsttest "FlEC" --labelsecondtest QUIC --transform ratio --xlabel "one-way delay (ms)" --ylabel '$\frac{\#msg_{FlEC}}{\#msg_{QUIC}}$' --ylim 0.9,1.1 --ylog --yticks "0.9,1,1.1=0.9,,1.1" --xticks 5,25,50,75,100,125,150,175,200 --title '$bw$ = 8Mbps, $loss$ = 1\%, $deadline$ = 250ms' --labelfirsttest "FlEC" --labelsecondtest "QUIC" --legends '$FlEC_{API}$,$FlEC_{NO-API}$' -t results_plots/messages_loss_1_long_deliveries_pct_with_and_without_api.pdf



# bbr experimental design
python3 plot_results.py --namefirsttest simple_fec_message_bbr --namesecondtest bbr --transform ratio -m CDF -f results_db/messages_experimental_design.db --metric message_long_deliveries_pct,server_bytes_sent --filesize 5000000,0,0,0 --xlabel "ratio" --labelfirsttest "FlEC" --labelsecondtest "QUIC" --ylabel "CDF" --xlim 0.5,2 --ylim 0,1 --xticks "0.5,0.75,1,1.33,2=0.5,0.75,1,1.33,2" --log --title '$RTT \in [10, 400]ms$, $bw \in [0.8, 30]Mbps$, $loss \in [0.1, 3]\%$' -t results_plots/messages_experimental_design.pdf --legends '$\frac{\#msg_{FlEC}}{\#msg_{QUIC}}$,$\frac{bytes_{FlEC}}{bytes_{QUIC}}$'

