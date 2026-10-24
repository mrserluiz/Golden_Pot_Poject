package br.com.ethercraft.goldenpot;
import com.google.gson.*;
import java.io.*;
import java.nio.file.*;
import java.util.*;
import java.util.zip.*;

final class Resources {
 static final Gson JSON=new GsonBuilder().setPrettyPrinting().create();
 static final String STATE="minecraft:note_block[instrument=flute,note=24,powered=false]";
 static final String ID="goldenpot:ambrosio_ore";
 static final String TEXTURE="assets/ether/textures/item/Aether/ambrosio_ore.png";
 static JsonObject object(String text){return JsonParser.parseString(text).getAsJsonObject();}
 static byte[] json(JsonObject value){return JSON.toJson(value).getBytes(java.nio.charset.StandardCharsets.UTF_8);}
 static Map<String,byte[]> load(Path path)throws IOException{
  Map<String,byte[]> map=new TreeMap<>();long total=0;
  try(ZipInputStream in=new ZipInputStream(Files.newInputStream(path))){ZipEntry e;
   while((e=in.getNextEntry())!=null){
    String n=e.getName();if(n.startsWith("/")||n.contains("\\")||Arrays.asList(n.split("/")).contains(".."))throw new IOException("Unsafe pack entry: "+n);
    if(e.isDirectory())continue;byte[] bytes=in.readNBytes(32*1024*1024+1);total+=bytes.length;
    if(bytes.length>32*1024*1024||total>256*1024*1024)throw new IOException("Pack size limit exceeded");
    if(map.putIfAbsent(n,bytes)!=null)throw new IOException("Duplicate entry: "+n);
   }
  }return map;
 }
 static void write(Path path, Map<String,byte[]> entries)throws IOException{
  Path temp=Files.createTempFile(path.getParent(),"pack-",".tmp");
  try{
   try(ZipOutputStream out=new ZipOutputStream(Files.newOutputStream(temp))){for(var e:entries.entrySet()){ZipEntry z=new ZipEntry(e.getKey());z.setTime(0);out.putNextEntry(z);out.write(e.getValue());out.closeEntry();}}
   try{Files.move(temp,path,StandardCopyOption.REPLACE_EXISTING,StandardCopyOption.ATOMIC_MOVE);}catch(AtomicMoveNotSupportedException ex){Files.move(temp,path,StandardCopyOption.REPLACE_EXISTING);}
  }finally{Files.deleteIfExists(temp);}
 }
 static void add(Map<String,byte[]> m,String key,byte[] value)throws IOException{
  byte[] old=m.putIfAbsent(key,value);if(old!=null&&!Arrays.equals(old,value))throw new IOException("Resource conflict: "+key);
 }
 static void prepare(Path root, java.util.function.Function<String,InputStream> resource, boolean experimental)throws IOException{
  Files.createDirectories(root.resolve("sources"));Files.createDirectories(root.resolve("generated"));
  for(String edition:List.of("java","bedrock")){
   Path source=root.resolve("sources/"+edition+"-base.zip");
   if(!Files.exists(source))try(InputStream in=resource.apply("packs/"+edition+"-base.zip")){if(in==null)throw new IOException("Embedded pack missing");Files.copy(in,source);}
  }
  MappingInstaller.prepare(root,resource);
  Map<String,byte[]> j=load(root.resolve("sources/java-base.zip")),b=load(root.resolve("sources/bedrock-base.zip"));
  MappingInstaller.repairOfficialPickaxe(j,b);
  MappingInstaller.audit(root,j,b);
  // Keep official pack identity; bump only generated version to invalidate client cache.
  JsonObject manifest=object(new String(b.get("manifest.json"),java.nio.charset.StandardCharsets.UTF_8));
  manifest.getAsJsonObject("header").add("version",JsonParser.parseString("[0,2,1]"));
  for(JsonElement module:manifest.getAsJsonArray("modules"))module.getAsJsonObject().add("version",JsonParser.parseString("[0,2,1]"));
  b.put("manifest.json",json(manifest));
  if(!experimental){write(root.resolve("generated/EtherTexture-Java-GoldenPotGen.zip"),j);write(root.resolve("generated/EtherTexture-Bedrock-GoldenPotGen.mcpack"),b);return;}
  byte[] png=j.get(TEXTURE);if(png==null)throw new IOException("Official Ambrosio texture missing");
  // Use multipart inverse conditions to preserve every other state, including new instruments.
  JsonObject states=object("{\"multipart\":[{\"when\":{\"OR\":[{\"instrument\":\"!flute\"},{\"note\":\"!24\"},{\"powered\":\"true\"}]},\"apply\":{\"model\":\"minecraft:block/note_block\"}},{\"when\":{\"instrument\":\"flute\",\"note\":\"24\",\"powered\":\"false\"},\"apply\":{\"model\":\"goldenpot:block/ambrosio_ore\"}}]}");
  add(j,"assets/minecraft/blockstates/note_block.json",json(states));
  add(j,"assets/goldenpot/textures/block/ambrosio_ore.png",png);
  add(j,"assets/goldenpot/models/block/ambrosio_ore.json",json(object("{\"parent\":\"minecraft:block/cube_all\",\"textures\":{\"all\":\"goldenpot:block/ambrosio_ore\"}}")));
  add(j,"assets/goldenpot/items/ambrosio_ore.json",json(object("{\"model\":{\"type\":\"minecraft:model\",\"model\":\"goldenpot:block/ambrosio_ore\"}}")));
  add(b,"textures/goldenpot/ambrosio_ore.png",png);
  for(String atlas:List.of("terrain_texture","item_texture")){
   String key="textures/"+atlas+".json";byte[] data=b.get(key);if(data==null)throw new IOException("Missing atlas: "+key);
   JsonObject o=object(new String(data,java.nio.charset.StandardCharsets.UTF_8));
   JsonObject t=o.getAsJsonObject("texture_data");if(t==null)throw new IOException("Invalid atlas: "+key);
   if(t.has("gpg_ambrosio_ore"))throw new IOException("Reserved atlas ID already occupied");
   t.add("gpg_ambrosio_ore",object("{\"textures\":\"textures/goldenpot/ambrosio_ore\"}"));b.put(key,json(o));
  }
  write(root.resolve("generated/EtherTexture-Java-GoldenPotGen.zip"),j);
  write(root.resolve("generated/EtherTexture-Bedrock-GoldenPotGen.mcpack"),b);
  Files.writeString(root.resolve("registry.json"),JSON.toJson(object("{\"schema\":1,\"id\":\"goldenpot:ambrosio_ore\",\"carrier\":\""+STATE+"\",\"item_model\":\"goldenpot:ambrosio_ore\",\"custom_model_data\":720001,\"bedrock_name\":\"gpg_ambrosio_ore\"}")));
 }
}
