rule gather_binomials: # Not used, it's a lot of questions and genus is present in binomial, so might as well only test on genus
    input:
        "resources/records.zip"
    output:
        "results/input/taxa-species.tsv"
    shell:
        # unzip -p {input} | split -n r/1/5 | jq .indexTerms\
        """
        unzip -p {input} | jq .indexTerms\
        | mlr --ijson --otsv template -f "genus","specificepithet" --fill-with MISSING | grep -v MISSING\
        | mlr --tsv uniq -a\
        > {output}
        """

rule gather_taxa_for_upper_ranks:
    input:
        "resources/records.zip"
    output:
        "results/input/taxa-{rank}.tsv"
    shell:
        """
        unzip -p {input}\
        | jq .indexTerms\
        | jq "{{taxon: .{wildcards.rank}}}"\
        | mlr --ijson --otsv uniq -a\
        | grep -vE "^null$"\
        > {output}
        """

checkpoint make_taxonomy_questions:
    input:
        phylum="results/input/taxa-phylum.tsv",
        class_="results/input/taxa-class.tsv",
        order="results/input/taxa-order.tsv",
        family="results/input/taxa-family.tsv",
        genus="results/input/taxa-genus.tsv",
    output:
        "results/input/taxonomy-qa.tsv"
    script:
        "../scripts/make-taxonomy-qa-table.py"
