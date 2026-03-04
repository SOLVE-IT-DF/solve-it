# SOLVE-IT Knowledge Base

This is a generated markdown version of the SOLVE-IT knowledge base. See [GitHub repository](https://github.com/SOLVE-IT-DF/solve-it) for more details.



# Objective Index
- [Prepare for a digital investigation](#prepare-for-a-digital-investigation)
- [Find potential digital evidence sources](#find-potential-digital-evidence-sources)
- [Prioritize digital evidence sources](#prioritize-digital-evidence-sources)
- [Preserve digital evidence](#preserve-digital-evidence)
- [Acquire data](#acquire-data)
- [Gain access](#gain-access)
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

- 🟢 [T1005 - Conduct a search of a crime scene](md_content/T1005.md)
- 🟡 [T1006 - Digital sniffer dogs](md_content/T1006.md)
- 🟢 [T1007 - Use a SyncTriage-based approach to detect existence of devices](md_content/T1007.md)
- 🔴 [T1008 - Profiling network traffic](md_content/T1008.md)
- 🔴 [T1009 - Locate cloud account identifiers](md_content/T1009.md)
<a id="prioritize-digital-evidence-sources"></a>
### Prioritize digital evidence sources
*Rank the evidence sources based on their relevance and potential value to the investigation.*

- 🟢 [T1001 - Triage](md_content/T1001.md)
<a id="preserve-digital-evidence"></a>
### Preserve digital evidence
*Ensure the integrity and authenticity of digital evidence is maintained.*

- 🟢 [T1010 - Place device in faraday environment](md_content/T1010.md)
- 🔴 [T1011 - Store seized devices in evidence bags](md_content/T1011.md)
- 🟢 [T1012 - Connect storage medium via hardware write blocker](md_content/T1012.md)
- 🔴 [T1013 - Use software write blockers to provide read only access to storage media](md_content/T1013.md)
- 🟡 [T1110 - Preserving reference data](md_content/T1110.md)
<a id="acquire-data"></a>
### Acquire data
*Collect data from the identified evidence sources.*

- 🟢 [T1002 - Disk imaging](md_content/T1002.md)
- 🟢 [T1003 - Memory imaging](md_content/T1003.md)
- 🟢 [T1004 - Selective file acquisition](md_content/T1004.md)
- 🟢 [T1015 - Privacy preserving selective extraction](md_content/T1015.md)
- 🟢 [T1016 - Live data collection](md_content/T1016.md)
- 🔴 [T1017 - Network packet capture](md_content/T1017.md)
- 🔴 [T1018 - Remote data collection](md_content/T1018.md)
- 🟢 [T1020 - Mobile file system extraction](md_content/T1020.md)
- 🔴 [T1022 - Mobile device screenshot based capture](md_content/T1022.md)
- 🔴 [T1023 - Cloud data collection to access data via a live web page using credentials](md_content/T1023.md)
- 🔴 [T1024 - Cloud data collection via submission of request to service provider](md_content/T1024.md)
- 🟢 [T1025 - Writing data to a forensic image format](md_content/T1025.md)
- 🟢 [T1026 - Writing data to standard archive format](md_content/T1026.md)
- 🔴 [T1028 - Chip-off](md_content/T1028.md)
- 🔴 [T1029 - Access data from a desoldered eMMC via a chip reader](md_content/T1029.md)
- 🔴 [T1030 - Data read from unmanaged NAND](md_content/T1030.md)
- 🔴 [T1104 - Collect data using open source intelligence](md_content/T1104.md)
- 🟡 [T1111 - Recording system clock offset](md_content/T1111.md)
- 🟢 [T1112 - Physical disk identification and removal](md_content/T1112.md)
- 🟢 [T1113 - Access internal storage via bootable environment](md_content/T1113.md)
- 🟡 [T1114 - Memory Acquisition via Cold Boot Attack](md_content/T1114.md)
- 🟢 [T1157 - Extract device data using exposed service](md_content/T1157.md)
    - 🟢 [T1019 - Mobile backup extraction](md_content/T1019.md)
- 🟢 [T1159 - Extract mobile data via deployed agent](md_content/T1159.md)
- 🔴 [T1160 - Collect data with 'cloud backup restore' approach](md_content/T1160.md)
- 🔴 [T1162 - Read data from a device via In-System Programming (ISP)](md_content/T1162.md)
    - 🔴 [T1027 - Data read using JTAG](md_content/T1027.md)
- 🔴 [T1163 - Automated screenshot-based capture of a mobile device](md_content/T1163.md)
- 🟢 [T1164 - Direct data read from a block device](md_content/T1164.md)
- 🟢 [T1166 - Connect directly to storage media](md_content/T1166.md)
<a id="gain-access"></a>
### Gain access
*Attempt to gain access to protected data sources or other restricted data.*

- 🟢 [T1031 - Key recovery from memory](md_content/T1031.md)
- 🔴 [T1032 - Side channel](md_content/T1032.md)
- 🔴 [T1033 - Extraction of credential from an accessible device](md_content/T1033.md)
- 🟢 [T1034 - Brute force attack](md_content/T1034.md)
- 🟢 [T1035 - Dictionary attack](md_content/T1035.md)
- 🔴 [T1036 - Smudge attack](md_content/T1036.md)
- 🔴 [T1037 - Obtain password from the device owner](md_content/T1037.md)
- 🔴 [T1038 - Rainbow table-based password attack](md_content/T1038.md)
- 🔴 [T1039 - App downgrade](md_content/T1039.md)
- 🟡 [T1040 - Use mobile device exploit](md_content/T1040.md)
- 🔴 [T1041 - Pin2Pwn](md_content/T1041.md)
- 🟢 [T1158 - Configure device to enable a service needed for data extraction](md_content/T1158.md)
<a id="read-data-from-digital-evidence-storage-formats"></a>
### Read data from digital evidence storage formats
*Access data within digital evidence containers such as disk images, memory dumps, or archive formats.*

- 🟢 [T1042 - Disk image hash verification](md_content/T1042.md)
- 🟢 [T1043 - Decode forensic image container format](md_content/T1043.md)
- 🟡 [T1044 - Mobile backup decoding](md_content/T1044.md)
- 🟢 [T1045 - Decode standard archive format](md_content/T1045.md)
- 🔴 [T1102 - Decode data from image from unmanaged NAND](md_content/T1102.md)
<a id="reduce-data-under-consideration"></a>
### Reduce data under consideration
*Filter the data to be considered in the investigation for practical, legal, or privacy protection reasons.*

- 🔴 [T1046 - Privileged material protection](md_content/T1046.md)
- 🟡 [T1047 - Hash matching (reduce)](md_content/T1047.md)
- 🔴 [T1048 - Privacy protection via partial processing](md_content/T1048.md)
<a id="access-partitions,-volumes-and-file-systems-data"></a>
### Access partitions, volumes and file systems data
*Process core data storage structures such as partitions, volumes, and file systems, recovering content and metadata.*

- 🟢 [T1059 - Identify partitions](md_content/T1059.md)
- 🟢 [T1060 - Enumerate allocated files and folders](md_content/T1060.md)
- 🟢 [T1061 - Recover non-allocated files](md_content/T1061.md)
    - 🟢 [T1150 - Recover non-allocated files using residual file metadata](md_content/T1150.md)
    - 🟢 [T1064 - File carving](md_content/T1064.md)
- 🔴 [T1062 - Decryption of encrypted file systems/volumes](md_content/T1062.md)
- 🟢 [T1063 - Identify file types](md_content/T1063.md)
<a id="extract-artifacts-stored-by-the-operating-system"></a>
### Extract artifacts stored by the operating system
*Process data stored by the operating system to extract digital forensic artifacts.*

- 🔴 [T1065 - Content indexer examination (OS)](md_content/T1065.md)
- 🔴 [T1066 - Log file examination (OS)](md_content/T1066.md)
- 🔴 [T1067 - Cloud synchronisation feature examination (OS)](md_content/T1067.md)
- 🔴 [T1068 - Recently used file identification (OS)](md_content/T1068.md)
- 🔴 [T1083 - Memory examination (OS-level)](md_content/T1083.md)
- 🔴 [T1096 - Run programs identification (OS)](md_content/T1096.md)
- 🔴 [T1097 - Installed programs identification (OS)](md_content/T1097.md)
- 🔴 [T1098 - User account analysis (OS)](md_content/T1098.md)
- 🟢 [T1116 - Determine connected devices](md_content/T1116.md)
- 🔴 [T1149 - File versioning feature examination](md_content/T1149.md)
<a id="extract-artifacts-stored-by-applications"></a>
### Extract artifacts stored by applications
*Process data stored by the applications to extract digital forensic artifacts.*

- 🟢 [T1069 - Browser examination](md_content/T1069.md)
    - 🟢 [T1137 - Browser history examination](md_content/T1137.md)
    - 🟢 [T1138 - Browser cache examination](md_content/T1138.md)
    - 🔴 [T1139 - Browser session examination](md_content/T1139.md)
    - 🔴 [T1140 - Browser autofill examination](md_content/T1140.md)
    - 🟡 [T1141 - Browser bookmarks examination](md_content/T1141.md)
    - 🟡 [T1142 - Browser downloads examination](md_content/T1142.md)
    - 🔴 [T1143 - Browser configuration examination](md_content/T1143.md)
    - 🟢 [T1144 - Browser profile enumeration](md_content/T1144.md)
    - 🔴 [T1145 - Browser extensions examination](md_content/T1145.md)
    - 🔴 [T1146 - Browser synchronization feature examination](md_content/T1146.md)
    - 🔴 [T1147 - Browser cookie examination](md_content/T1147.md)
    - 🔴 [T1148 - Browser web storage examination](md_content/T1148.md)
- 🔴 [T1070 - Email examination](md_content/T1070.md)
- 🟢 [T1072 - Chat app examination](md_content/T1072.md)
- 🔴 [T1073 - Calendar app examination](md_content/T1073.md)
- 🔴 [T1074 - Social network app examination](md_content/T1074.md)
- 🔴 [T1075 - Maps/travel app examination](md_content/T1075.md)
- 🔴 [T1077 - Photos app examination](md_content/T1077.md)
- 🔴 [T1078 - Cloud sync app examination](md_content/T1078.md)
- 🔴 [T1105 - Memory examination (application-level)](md_content/T1105.md)
- 🔴 [T1107 - Health/Fitness app examination](md_content/T1107.md)
- 🔴 [T1108 - Reminders app examination](md_content/T1108.md)
- 🔴 [T1109 - Payment app examination](md_content/T1109.md)
- 🟢 [T1133 - AI companion app examination](md_content/T1133.md)
<a id="extract-artifacts,-or-content-of-specific-types"></a>
### Extract artifacts, or content of specific types
*Process data to extract artifacts or stored content of specific types.*

- 🔴 [T1021 - Configuration file examination](md_content/T1021.md)
- 🟢 [T1052 - Timeline generation](md_content/T1052.md)
    - 🟢 [T1153 - Apply offset to a timestamp](md_content/T1153.md)
- 🔴 [T1053 - Entity extraction](md_content/T1053.md)
- 🔴 [T1056 - Entity connection enumeration](md_content/T1056.md)
- 🟢 [T1071 - Database examination](md_content/T1071.md)
- 🟢 [T1076 - Log file examination](md_content/T1076.md)
- 🔴 [T1099 - File repair with grafting](md_content/T1099.md)
- 🔴 [T1100 - EXIF data extraction](md_content/T1100.md)
- 🟢 [T1120 - Automated artifact extraction](md_content/T1120.md)
<a id="locate-potentially-relevant-content"></a>
### Locate potentially relevant content
*Attempt to find digital artifacts relevant to the investigation.*

- 🟢 [T1049 - Keyword searching](md_content/T1049.md)
    - 🟢 [T1125 - Keyword search (live)](md_content/T1125.md)
    - 🟢 [T1126 - Keyword search (live) (physical)](md_content/T1126.md)
    - 🟢 [T1127 - Keyword search (live) (logical)](md_content/T1127.md)
    - 🟢 [T1124 - Keyword search (indexed)](md_content/T1124.md)
    - 🟢 [T1121 - Keyword indexing](md_content/T1121.md)
    - 🟢 [T1122 - Keyword search (case-type wordlists)](md_content/T1122.md)
    - 🟢 [T1123 - Keyword search (case-specific wordlists)](md_content/T1123.md)
    - 🟢 [T1151 - Keyword search (over extracted artifacts)](md_content/T1151.md)
- 🟡 [T1050 - Hash matching (locate)](md_content/T1050.md)
- 🔴 [T1051 - Fuzzy hash matching](md_content/T1051.md)
- 🟢 [T1086 - Timeline analysis](md_content/T1086.md)
    - 🟢 [T1134 - Use time anchors to estimate clock offset](md_content/T1134.md)
- 🟢 [T1118 - Locate relevant files by path](md_content/T1118.md)
<a id="review-content-for-relevance"></a>
### Review content for relevance
*Review potentially relevant content to determine its significance or meaning.*

- 🟢 [T1054 - Manual content review for relevant material](md_content/T1054.md)
- 🔴 [T1055 - File system content inspection](md_content/T1055.md)
- 🔴 [T1079 - Audio content analysis](md_content/T1079.md)
- 🔴 [T1080 - Video content analysis](md_content/T1080.md)
    - 🔴 [T1106 - Deep fake detection (video)](md_content/T1106.md)
- 🔴 [T1081 - Image content analysis](md_content/T1081.md)
- 🔴 [T1082 - Document content analysis](md_content/T1082.md)
<a id="detect-anti-forensics-and-other-anomalies"></a>
### Detect anti-forensics and other anomalies
*Search for indicators of anti-forensic techniques or other anomalies such as malware, which could affect interpretation.*

- 🔴 [T1057 - Search for indicators of steganography](md_content/T1057.md)
- 🔴 [T1058 - Search for mismatched file extensions](md_content/T1058.md)
- 🔴 [T1128 - Search for indicators of malware](md_content/T1128.md)
- 🔴 [T1129 - Search for indicators of clock tampering](md_content/T1129.md)
- 🔴 [T1130 - Search for indicators of encrypted data](md_content/T1130.md)
- 🔴 [T1131 - Search for indicators of trail obfuscation](md_content/T1131.md)
- 🔴 [T1132 - Search for indicators of artifact wiping](md_content/T1132.md)
<a id="establish-identities"></a>
### Establish identities
*Attempt to link data or devices to individuals.*

- 🔴 [T1084 - Extraction of user accounts](md_content/T1084.md)
- 🔴 [T1085 - Identify conflation](md_content/T1085.md)
<a id="create-visualizations"></a>
### Create visualizations
*Display information using visual representations to assist with analysis.*

- 🔴 [T1103 - Virtualise suspect system for previewing](md_content/T1103.md)
- 🔴 [T1115 - Visualisation of geolocation information](md_content/T1115.md)
<a id="reconstruct-events"></a>
### Reconstruct events
*Use available digital evidence to formulate and test hypotheses about events.*

- 🔴 [T1087 - Location-based event reconstruction](md_content/T1087.md)
- 🔴 [T1088 - Relational-based event reconstruction](md_content/T1088.md)
- 🟢 [T1117 - Time-based event reconstruction](md_content/T1117.md)
- 🔴 [T1154 - Identity-based event reconstruction](md_content/T1154.md)
- 🔴 [T1155 - Operation-based event reconstruction](md_content/T1155.md)
- 🔴 [T1156 - Functional-based event reconstruction](md_content/T1156.md)
<a id="conduct-research"></a>
### Conduct research
*Conduct research to gain additional knowledge to support the acquisition, extraction, or interpretation of digital evidence.*

- 🔴 [T1089 - Source code review](md_content/T1089.md)
- 🔴 [T1090 - Experimentation](md_content/T1090.md)
- 🔴 [T1095 - Instrumentation](md_content/T1095.md)
- 🔴 [T1101 - Cell site survey](md_content/T1101.md)
- 🟢 [T1119 - Automatically scan for artifact changes caused by app updates](md_content/T1119.md)
<a id="produce-documentation"></a>
### Produce documentation
*Create documentation about techniques used and findings.*

- 🔴 [T1014 - Chain of custody documentation](md_content/T1014.md)
- 🟡 [T1091 - Bookmark artifacts](md_content/T1091.md)
- 🟢 [T1092 - Produce tag-based automated report](md_content/T1092.md)
- 🔴 [T1093 - Write expert report](md_content/T1093.md)
- 🔴 [T1094 - Disclosure](md_content/T1094.md)


---

*Markdown generated: 2026-03-04 08:14:46*
