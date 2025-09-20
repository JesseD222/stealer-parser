Using Python and FastStream generate the code for a modular, async, ETL pipeline with these key features and functionality:
- modular and configurable, each processing step can be an independent publisher/subscriber 
- Configured with simple python dictionary objects and the Strategy pattern, it's dependencies (inputs), function arguments, and what it produces (outputs). Each source ExtractionTask can have it's own configurable set of processing strategies including a chunk generator, an extractor function, a transform function, and a loader function. The specific strategy implementation for each it part of the extraction details of the ExtractionConfiguration and each DataField it contains.
- regex based text record extraction from semi-structured files, batched in groups of of files in directories called Data Units, a batch may contain many data unit directories, but each data unit contains text files with records local to that data unit only. The order of records extracted from a ExtractionTask (which is usually a single file, or directory of files with the same record type) is not important, but the order of individual data fields must be kept together if not in the exact order because they are part of the same data record.
- Domain models and repository service pattern with the Advanced-Alchemy library stand alone and not as a part of an ASGI like Litestar. Use current Domain models including: Machine, DataUnit, ExtractionTask, ExtractionConfiguration, DataField, Record and it's polymorph heirarchy of Credential, Autofill, Cookie, SystemInformation, Piece, UserFile, and Vault
- preprocessing by extraction of raw "label: field_data" into nested list/dict structure and published to be consumed and further identified by the transform stage using Structural Pattern Matching to identify the sets of fields by alias and normalized into Record subtypes by the polymorph heirarchy and it's repository and services.
- Do not use stacked IF/THEN/ELSE chains to select runtime functions, instead use composition and Abstract Factory patterns to create a registry implementation with caching, singletons where possible etc.

Example data processing flow:

1. A Batch load is requested and the top level directory is specified, "/filesystem/Batch_1/"
2. The batch directory is iterated and individual DataUnit source directories are identified (AA123 is the DataUnit dir), "/filesystem/Batch/AA123/"
3. The DataUnit source path is published to the extraction channel. Example message: {'DataUnit' AA123 of Batch_1: /filesystem/Batch_1/AA123/}
4. The DataUnit source task is picked up by the first work cell which is the DataUnit Inspector, it's task is to identify files contained within the DataUnit that hold Records to be extracted, the type of record may be determined at this point by the filename and it's path relative to the DataUnit root, These details are provided by the ExtractionConfiguration which are enabled or chosen when the batch job is requested, each ExtractionConfiguration represents a single record type and source file/directory. The ExtractionConfiguration has a list of DataFields which provide the specific extraction details for each field of the record.
5. Each identified ExtractionTask, along with it's task details, is published to the extraction channel.
6. Each ExtractionTask task message is picked up by a Chunk Generator which iterates the source item(s) and produces Chunk items for each individual record discovered. The Chunk Generator uses again the ExtractionConfiguration to identify the boundary separators or strategy between records.
7. Each Chunk of the ExtractionTask is published to the channel.
8. Each Chunk(Record) item is picked up by an ExtractionWorker, which selects it's strategy based on the DataField items contained in the ExtractionConfiguration, using the strategy the actual record fields are extracted. IMPORTANT: ALL DATA FIELDS  EXTRACTED STAY TOGETHER AS PART OF THIS RECORD
9. Raw records are published and consumed by the Transform Workers in the same manner as the ExtractionWorkers and published to the output channel as completed records
10. The final Loader Workers consume the completed records and organize them by ExtractionTask, DataUnit, and the Batch and are persisted to the database through the SQLAlchemyAsyncRepository and Service components.

Task configuration heirarchy:
ExtractionConfiguration > contains many DataField > contains identifier aliases and extraction details for a single data field element

Data entities produced by the pipeline:
DataUnit > contains many ExtractionTasks > contains many Record items which are joined to specific record type subclasses eg. Credential, Autofill, Piece, Vault, UserFile

There are 2 heirarchies of Domain entities, 1. the Extraction Configuration module which represents a library of configured data sources and their related identifiers and extraction parameters. 2. The DataUnits which represent a single package of records extracted from a single source, and the ExtractionTasks which represent the records of each type extracted, and which contain the Records of that type extracted from one or more files of that DataUnit.

The input to the Pipeline is a selection of desired Record types to be extracted from a batch of several source items.
The Output is several DataUnits containing records of the selected type which are validated and unique within the specific parent DataUnit and the Batch

Use the FastStream Redis broker type and construct the Pipeline. Generate Async compatible code at all times and maximize concurency by creating multiple message channels if necessary, all data flow between stages and workers should be via the messaging channels. Records are the smallest divisible unit of work and must be kept together as a set of fields. Processing order is not important except that all records from all files within a DataUnit root directory should be completed as a unit within the timeframe of the batch request and execution. Processing of items may be postponed due to dependencies within the batch or dataunit scopes.