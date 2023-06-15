FROM gcc

WORKDIR /app

COPY . .

COPY run.sh .

RUN touch test3.txt

RUN gcc given_sim.c -lm -lpthread -o given_sim

#CMD ["touch", "test2.txt", "&&", "./given_sim", ">>", "ouput.txt"]

RUN chmod 777 run.sh
RUN chmod 777 tc.sh

CMD ["./run.sh"]
