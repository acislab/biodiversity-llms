from glob import glob

rule clean_raws:
    input:
        glob(config["raw_dir"] + "/*.jsonl")
    output:
        PRESENCE_IN_UNFILTERED
    params:
        fields=",".join([f'"{field}' for field in config["qa_fields"]])
    log:
        "logs/clean_raws.log"
    shell:
        """
        cat {input:q}\
        | jq .indexTerms\
        | mlr --ijson --otsv template -f {params.fields} --fill-with MISSING\
        | grep -v MISSING\
        | mlr --tsv uniq -a\
        | python3 workflow/scripts/clean-records.py\
        1> {output} 2> {log}
        """

checkpoint filter_raws_to_presence_tsv:
    input:
        PRESENCE_IN_UNFILTERED
    output:
        PRESENCE_IN
    script:
        "../scripts/filter-records.py"
