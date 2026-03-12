# SOLVE-IT Knowledge Base

This is a generated markdown version of the SOLVE-IT knowledge base. See [GitHub repository](https://github.com/SOLVE-IT-DF/solve-it) for more details.



# Objective Index
- [Prepare for a digital investigation](#prepare-for-a-digital-investigation)
- [Find potential digital evidence sources](#find-potential-digital-evidence-sources)
- [Prioritize digital evidence sources](#prioritize-digital-evidence-sources)
- [Preserve digital evidence](#preserve-digital-evidence)
- [Access device data for acquisition](#access-device-data-for-acquisition)
- [Overcome protection mechanisms](#overcome-protection-mechanisms)
- [Acquire data](#acquire-data)
- [Store acquired data](#store-acquired-data)
- [Read data from digital evidence storage formats](#read-data-from-digital-evidence-storage-formats)
- [Reduce data under consideration](#reduce-data-under-consideration)
- [Access partitions, volumes and file systems data](#access-partitions,-volumes-and-file-systems-data)
- [Extract artifacts stored by the operating system](#extract-artifacts-stored-by-the-operating-system)
- [Extract artifacts stored by applications](#extract-artifacts-stored-by-applications)
- [Extract artifacts, or content of specific types](#extract-artifacts,-or-content-of-specific-types)
- [Locate potentially relevant content](#locate-potentially-relevant-content)
- [Review content for relevance](#review-content-for-relevance)
- [Detect anti-forensics and other anomalies](#detect-anti-forensics-and-other-anomalies)
- [Establish identities](#establish-identities)
- [Create visualizations](#create-visualizations)
- [Reconstruct events](#reconstruct-events)
- [Conduct research](#conduct-research)
- [Produce documentation](#produce-documentation)

# Objectives and Techniques
<a id="prepare-for-a-digital-investigation"></a>
### Prepare for a digital investigation
*Conduct activities in preparation of conducting a digital investigation*

<a id="find-potential-digital-evidence-sources"></a>
### Find potential digital evidence sources
*Locate sources of digital evidence that may be relevant to the investigation.*

- [DFT-1005 - Conduct a search of a crime scene](md_content/DFT-1005.md)
- [DFT-1006 - Digital sniffer dogs](md_content/DFT-1006.md)
- [DFT-1007 - Use a SyncTriage-based approach to detect existence of devices](md_content/DFT-1007.md)
- [DFT-1008 - Profiling network traffic](md_content/DFT-1008.md)
- [DFT-1009 - Locate cloud account identifiers](md_content/DFT-1009.md)
<a id="prioritize-digital-evidence-sources"></a>
### Prioritize digital evidence sources
*Rank the evidence sources based on their relevance and potential value to the investigation.*

- [DFT-1001 - Triage](md_content/DFT-1001.md)
<a id="preserve-digital-evidence"></a>
### Preserve digital evidence
*Ensure the integrity and authenticity of digital evidence is maintained.*

- [DFT-1010 - Place device in faraday environment](md_content/DFT-1010.md)
- [DFT-1011 - Store seized devices in evidence bags](md_content/DFT-1011.md)
- [DFT-1012 - Connect storage medium via hardware write blocker](md_content/DFT-1012.md)
- [DFT-1013 - Use software write blockers to provide read only access to storage media](md_content/DFT-1013.md)
- [DFT-1110 - Preserving reference data](md_content/DFT-1110.md)
<a id="access-device-data-for-acquisition"></a>
### Access device data for acquisition
*Connect to physical sources of digital evidence to facilitate data extraction*

- [DFT-1028 - Chip-off](md_content/DFT-1028.md)
- [DFT-1029 - Access data from a desoldered eMMC via a chip reader](md_content/DFT-1029.md)
- [DFT-1112 - Physical disk identification and removal](md_content/DFT-1112.md)
- [DFT-1113 - Access internal storage via bootable environment](md_content/DFT-1113.md)
- [DFT-1166 - Connect directly to storage media](md_content/DFT-1166.md)
- [DFT-1171 - Access file system via live operating system](md_content/DFT-1171.md)
<a id="overcome-protection-mechanisms"></a>
### Overcome protection mechanisms
*Attempt to gain access to protected data sources or other restricted data.*

- [DFT-1031 - Key recovery from memory](md_content/DFT-1031.md)
- [DFT-1032 - Side channel](md_content/DFT-1032.md)
- [DFT-1033 - Extraction of credential from an accessible device](md_content/DFT-1033.md)
- [DFT-1034 - Brute force attack](md_content/DFT-1034.md)
- [DFT-1035 - Dictionary attack](md_content/DFT-1035.md)
- [DFT-1036 - Smudge attack](md_content/DFT-1036.md)
- [DFT-1037 - Obtain password from the device owner](md_content/DFT-1037.md)
- [DFT-1038 - Rainbow table-based password attack](md_content/DFT-1038.md)
- [DFT-1039 - App downgrade](md_content/DFT-1039.md)
- [DFT-1040 - Use mobile device exploit](md_content/DFT-1040.md)
- [DFT-1041 - Pin2Pwn](md_content/DFT-1041.md)
- [DFT-1158 - Configure device to enable a service needed for data extraction](md_content/DFT-1158.md)
<a id="acquire-data"></a>
### Acquire data
*Collect data from the identified evidence sources.*

- [DFT-1002 - Disk imaging](md_content/DFT-1002.md)
- [DFT-1003 - Memory imaging](md_content/DFT-1003.md)
- [DFT-1004 - Selective file acquisition](md_content/DFT-1004.md)
- [DFT-1015 - Privacy preserving selective extraction](md_content/DFT-1015.md)
- [DFT-1016 - Live data collection](md_content/DFT-1016.md)
- [DFT-1017 - Network packet capture](md_content/DFT-1017.md)
- [DFT-1018 - Remote data collection](md_content/DFT-1018.md)
- [DFT-1020 - Mobile file system extraction](md_content/DFT-1020.md)
- [DFT-1022 - Mobile device screenshot based capture](md_content/DFT-1022.md)
- [DFT-1023 - Cloud data collection to access data via a live web page using credentials](md_content/DFT-1023.md)
- [DFT-1024 - Cloud data collection via submission of request to service provider](md_content/DFT-1024.md)
- [DFT-1030 - Data read from unmanaged NAND](md_content/DFT-1030.md)
- [DFT-1104 - Collect data using open source intelligence](md_content/DFT-1104.md)
- [DFT-1111 - Recording system clock offset](md_content/DFT-1111.md)
- [DFT-1114 - Memory Acquisition via Cold Boot Attack](md_content/DFT-1114.md)
- [DFT-1157 - Extract device data using exposed service](md_content/DFT-1157.md)
    - [DFT-1019 - Mobile backup extraction](md_content/DFT-1019.md)
- [DFT-1159 - Extract mobile data via deployed agent](md_content/DFT-1159.md)
- [DFT-1160 - Collect data with 'cloud backup restore' approach](md_content/DFT-1160.md)
- [DFT-1162 - Read data from a device via In-System Programming (ISP)](md_content/DFT-1162.md)
    - [DFT-1027 - Data read using JTAG](md_content/DFT-1027.md)
- [DFT-1163 - Automated screenshot-based capture of a mobile device](md_content/DFT-1163.md)
- [DFT-1164 - Direct data read from a block device](md_content/DFT-1164.md)
- [DFT-1175 - Extract data using content queries](md_content/DFT-1175.md)
<a id="store-acquired-data"></a>
### Store acquired data
*Store acquired data in one or more formats for subsequent examination and analysis*

- [DFT-1025 - Writing bitstream data to a forensic image format](md_content/DFT-1025.md)
- [DFT-1026 - Writing data to standard archive format](md_content/DFT-1026.md)
<a id="read-data-from-digital-evidence-storage-formats"></a>
### Read data from digital evidence storage formats
*Access data within digital evidence containers such as disk images, memory dumps, or archive formats.*

- [DFT-1042 - Hash verification of source device against stored data](md_content/DFT-1042.md)
- [DFT-1043 - Access forensic image content (bitstream)](md_content/DFT-1043.md)
- [DFT-1044 - Mobile backup decoding](md_content/DFT-1044.md)
- [DFT-1045 - Decode standard archive format](md_content/DFT-1045.md)
- [DFT-1102 - Decode data from image from unmanaged NAND](md_content/DFT-1102.md)
- [DFT-1170 - Decode forensic image format (logical)](md_content/DFT-1170.md)
- [DFT-1172 - Access raw image content](md_content/DFT-1172.md)
- [DFT-1173 - Extract data from captured screenshots](md_content/DFT-1173.md)
- [DFT-1174 - Read evidential files stored directly on local file system](md_content/DFT-1174.md)
<a id="reduce-data-under-consideration"></a>
### Reduce data under consideration
*Filter the data to be considered in the investigation for practical, legal, or privacy protection reasons.*

- [DFT-1046 - Privileged material protection](md_content/DFT-1046.md)
- [DFT-1047 - Hash matching (reduce)](md_content/DFT-1047.md)
- [DFT-1048 - Privacy protection via partial processing](md_content/DFT-1048.md)
<a id="access-partitions,-volumes-and-file-systems-data"></a>
### Access partitions, volumes and file systems data
*Process core data storage structures such as partitions, volumes, and file systems, recovering content and metadata.*

- [DFT-1059 - Identify partitions](md_content/DFT-1059.md)
- [DFT-1060 - Enumerate allocated files and folders](md_content/DFT-1060.md)
- [DFT-1061 - Recover non-allocated files](md_content/DFT-1061.md)
    - [DFT-1150 - Recover non-allocated files using residual file metadata](md_content/DFT-1150.md)
    - [DFT-1064 - File carving](md_content/DFT-1064.md)
- [DFT-1062 - Decryption of encrypted file systems/volumes](md_content/DFT-1062.md)
- [DFT-1063 - Identify file types](md_content/DFT-1063.md)
- [DFT-1168 - Identify volumes](md_content/DFT-1168.md)
<a id="extract-artifacts-stored-by-the-operating-system"></a>
### Extract artifacts stored by the operating system
*Process data stored by the operating system to extract digital forensic artifacts.*

- [DFT-1065 - Content indexer examination (OS)](md_content/DFT-1065.md)
- [DFT-1066 - Log file examination (OS)](md_content/DFT-1066.md)
- [DFT-1067 - Cloud synchronisation feature examination (OS)](md_content/DFT-1067.md)
- [DFT-1068 - Recently used file identification (OS)](md_content/DFT-1068.md)
- [DFT-1083 - Memory examination (OS-level)](md_content/DFT-1083.md)
- [DFT-1096 - Run programs identification (OS)](md_content/DFT-1096.md)
- [DFT-1097 - Installed programs identification (OS)](md_content/DFT-1097.md)
- [DFT-1098 - User account analysis (OS)](md_content/DFT-1098.md)
- [DFT-1116 - Determine connected devices](md_content/DFT-1116.md)
- [DFT-1149 - File versioning feature examination](md_content/DFT-1149.md)
<a id="extract-artifacts-stored-by-applications"></a>
### Extract artifacts stored by applications
*Process data stored by the applications to extract digital forensic artifacts.*

- [DFT-1069 - Browser examination](md_content/DFT-1069.md)
    - [DFT-1137 - Browser history examination](md_content/DFT-1137.md)
    - [DFT-1138 - Browser cache examination](md_content/DFT-1138.md)
    - [DFT-1139 - Browser session examination](md_content/DFT-1139.md)
    - [DFT-1140 - Browser autofill examination](md_content/DFT-1140.md)
    - [DFT-1141 - Browser bookmarks examination](md_content/DFT-1141.md)
    - [DFT-1142 - Browser downloads examination](md_content/DFT-1142.md)
    - [DFT-1143 - Browser configuration examination](md_content/DFT-1143.md)
    - [DFT-1144 - Browser profile enumeration](md_content/DFT-1144.md)
    - [DFT-1145 - Browser extensions examination](md_content/DFT-1145.md)
    - [DFT-1146 - Browser synchronization feature examination](md_content/DFT-1146.md)
    - [DFT-1147 - Browser cookie examination](md_content/DFT-1147.md)
    - [DFT-1148 - Browser web storage examination](md_content/DFT-1148.md)
- [DFT-1070 - Email examination](md_content/DFT-1070.md)
- [DFT-1072 - Chat app examination](md_content/DFT-1072.md)
- [DFT-1073 - Calendar app examination](md_content/DFT-1073.md)
- [DFT-1074 - Social network app examination](md_content/DFT-1074.md)
- [DFT-1075 - Maps/travel app examination](md_content/DFT-1075.md)
- [DFT-1077 - Photos app examination](md_content/DFT-1077.md)
- [DFT-1078 - Cloud sync app examination](md_content/DFT-1078.md)
- [DFT-1105 - Memory examination (application-level)](md_content/DFT-1105.md)
- [DFT-1107 - Health/Fitness app examination](md_content/DFT-1107.md)
- [DFT-1108 - Reminders app examination](md_content/DFT-1108.md)
- [DFT-1109 - Payment app examination](md_content/DFT-1109.md)
- [DFT-1133 - AI companion app examination](md_content/DFT-1133.md)
<a id="extract-artifacts,-or-content-of-specific-types"></a>
### Extract artifacts, or content of specific types
*Process data to extract artifacts or stored content of specific types.*

- [DFT-1021 - Configuration file examination](md_content/DFT-1021.md)
- [DFT-1052 - Timeline generation](md_content/DFT-1052.md)
    - [DFT-1153 - Apply offset to a timestamp](md_content/DFT-1153.md)
- [DFT-1053 - Entity extraction](md_content/DFT-1053.md)
- [DFT-1056 - Entity connection enumeration](md_content/DFT-1056.md)
- [DFT-1071 - SQLite database examination](md_content/DFT-1071.md)
- [DFT-1076 - Log file examination](md_content/DFT-1076.md)
- [DFT-1099 - File repair with grafting](md_content/DFT-1099.md)
- [DFT-1100 - EXIF data extraction](md_content/DFT-1100.md)
- [DFT-1120 - Automated artifact extraction from app data](md_content/DFT-1120.md)
- [DFT-1167 - Extract search terms from URLs](md_content/DFT-1167.md)
- [DFT-1169 - Filter files related to an application](md_content/DFT-1169.md)
<a id="locate-potentially-relevant-content"></a>
### Locate potentially relevant content
*Attempt to find digital artifacts relevant to the investigation.*

- [DFT-1049 - Keyword searching](md_content/DFT-1049.md)
    - [DFT-1125 - Keyword search (live)](md_content/DFT-1125.md)
    - [DFT-1126 - Keyword search (live) (physical)](md_content/DFT-1126.md)
    - [DFT-1127 - Keyword search (live) (logical)](md_content/DFT-1127.md)
    - [DFT-1124 - Keyword search (indexed)](md_content/DFT-1124.md)
    - [DFT-1121 - Keyword indexing](md_content/DFT-1121.md)
    - [DFT-1122 - Keyword search (case-type wordlists)](md_content/DFT-1122.md)
    - [DFT-1123 - Keyword search (case-specific wordlists)](md_content/DFT-1123.md)
    - [DFT-1151 - Keyword search (over extracted artifacts)](md_content/DFT-1151.md)
- [DFT-1050 - Hash matching (locate)](md_content/DFT-1050.md)
- [DFT-1051 - Fuzzy hash matching](md_content/DFT-1051.md)
- [DFT-1086 - Timeline analysis](md_content/DFT-1086.md)
    - [DFT-1134 - Use time anchors to estimate clock offset](md_content/DFT-1134.md)
- [DFT-1118 - Locate relevant files by path](md_content/DFT-1118.md)
<a id="review-content-for-relevance"></a>
### Review content for relevance
*Review potentially relevant content to determine its significance or meaning.*

- [DFT-1054 - Manual content review for relevant material](md_content/DFT-1054.md)
- [DFT-1055 - File system content inspection](md_content/DFT-1055.md)
- [DFT-1079 - Audio content analysis](md_content/DFT-1079.md)
- [DFT-1080 - Video content analysis](md_content/DFT-1080.md)
    - [DFT-1106 - Deep fake detection (video)](md_content/DFT-1106.md)
- [DFT-1081 - Image content analysis](md_content/DFT-1081.md)
- [DFT-1082 - Document content analysis](md_content/DFT-1082.md)
<a id="detect-anti-forensics-and-other-anomalies"></a>
### Detect anti-forensics and other anomalies
*Search for indicators of anti-forensic techniques or other anomalies such as malware, which could affect interpretation.*

- [DFT-1057 - Search for indicators of steganography](md_content/DFT-1057.md)
- [DFT-1058 - Search for mismatched file extensions](md_content/DFT-1058.md)
- [DFT-1128 - Search for indicators of malware](md_content/DFT-1128.md)
- [DFT-1129 - Search for indicators of clock tampering](md_content/DFT-1129.md)
- [DFT-1130 - Search for indicators of encrypted data](md_content/DFT-1130.md)
- [DFT-1131 - Search for indicators of trail obfuscation](md_content/DFT-1131.md)
- [DFT-1132 - Search for indicators of artifact wiping](md_content/DFT-1132.md)
<a id="establish-identities"></a>
### Establish identities
*Attempt to link data or devices to individuals.*

- [DFT-1084 - Extraction of user accounts](md_content/DFT-1084.md)
- [DFT-1085 - Identify conflation](md_content/DFT-1085.md)
<a id="create-visualizations"></a>
### Create visualizations
*Display information using visual representations to assist with analysis.*

- [DFT-1103 - Virtualise suspect system for previewing](md_content/DFT-1103.md)
- [DFT-1115 - Visualisation of geolocation information](md_content/DFT-1115.md)
<a id="reconstruct-events"></a>
### Reconstruct events
*Use available digital evidence to formulate and test hypotheses about events.*

- [DFT-1087 - Location-based event reconstruction](md_content/DFT-1087.md)
- [DFT-1088 - Relational-based event reconstruction](md_content/DFT-1088.md)
- [DFT-1117 - Time-based event reconstruction](md_content/DFT-1117.md)
- [DFT-1154 - Identity-based event reconstruction](md_content/DFT-1154.md)
- [DFT-1155 - Operation-based event reconstruction](md_content/DFT-1155.md)
- [DFT-1156 - Functional-based event reconstruction](md_content/DFT-1156.md)
<a id="conduct-research"></a>
### Conduct research
*Conduct research to gain additional knowledge to support the acquisition, extraction, or interpretation of digital evidence.*

- [DFT-1089 - Source code review](md_content/DFT-1089.md)
- [DFT-1090 - Experimentation](md_content/DFT-1090.md)
- [DFT-1095 - Instrumentation](md_content/DFT-1095.md)
- [DFT-1101 - Cell site survey](md_content/DFT-1101.md)
- [DFT-1119 - Automatically scan for artifact changes caused by app updates](md_content/DFT-1119.md)
<a id="produce-documentation"></a>
### Produce documentation
*Create documentation about techniques used and findings.*

- [DFT-1014 - Chain of custody documentation](md_content/DFT-1014.md)
- [DFT-1091 - Bookmark artifacts](md_content/DFT-1091.md)
- [DFT-1092 - Produce tag-based automated report](md_content/DFT-1092.md)
- [DFT-1093 - Write expert report](md_content/DFT-1093.md)
- [DFT-1094 - Disclosure](md_content/DFT-1094.md)


---

*Markdown generated: 2026-03-12 13:47:49*
