from struct import unpack_from, pack
from numpy import array, array_equal
from BoundingBox import BoundingBox
from Triangle import *

def ReadZeroTerminatedString(reader: bytearray, address: int) -> str:
    end = reader[address:].index(b"\x00") + address
    return reader[address:end].decode('utf-8')

class CsbFile:
    Models: list[CsbFile.Model] = []
    Nodes: list[CsbFile.Node] = []
    Objects: list[CsbFile.CollisionObject] = []
    
    Unknown = 1
    Unknown3 = 2
    
    Unknown4 = 0xFE
    Unknown5 = 0x7
    
    SubModelBounding = BoundingBox() #min max vec3
    
    OldParenting = False
    
    class CollisionObject:
        Identifier1 = None
        Identifier2 = None
        Point1 = None
        Point2 = None
        Size = (0.0, 0.0, 0.0)
        Rotation = (0.0, 0.0, 0.0)
        
        Radius = 0.7 #if IsSphere == True
        
        BoxExtra = array((0.0, 0.0, 1.0, 0.0, 0.0, 0.0, 0.0, 1.0, 0.0))
        
        IsSphere = False
        
        ColFlag = None
        
        NodeIndex = None
        
        Name = None

    class Node:
        ID = None
        Flags = None
        NumChildren = None

    class Mesh:
        Name = None
        MaterialAttribute = None
        ColFlag = None
        
        NodeIndex = None
        
        NumVertices = None
        NumTriangles = None
        
        def __init__(self):
            self.Positions = list()
            self.Triangles: list[Triangle] = list()

    class Model:
        NumTriangles: int = 0
        NumVertices: int = 0
        
        Unknown0: int = 1
        ColFlag = None
        Unknown2 = None
        MaterialAttribute = None
        Unknown4 = None
        Unknown5: int = 1
        
        Zero: tuple[float, float, float] = (0.0, 0.0, 0.0)
        Translate: tuple[float, float, float] = None
        Rotation: tuple[float, float, float] = None
        
        NodeIndex = None
        
        
        #Default name when meshes are combined into one model buffer
        Name = "DEADBEEF"
        
        def __init__(self):
            self.Bounding = BoundingBox() #min max vec3
            
            self.Meshes: list[CsbFile.Mesh] = []
            
            self.Triangles: list[Triangle] = []
            self.Positions = []

    def Read(self, reader: bytearray, bigEndian: bool):
        
        byteOrder = '>' if bigEndian else '<'
        
        epsilon = 1e-9
        
        isVersion1 = True
        
        readOffset = 0
        
        #optional objects that form a sphere or box
        #these are generally used to trigger things
        num_sphere_objects = unpack_from(f'{byteOrder}I', reader, offset=readOffset)[0]
        readOffset += 4
        
        sphere_objects = [self.CollisionObject() for _ in range(num_sphere_objects)]
        for i in range(num_sphere_objects):
            sphere_objects[i].Identifier1 = unpack_from(f'{byteOrder}H', reader, offset=readOffset)[0]
            readOffset += 2
            sphere_objects[i].Identifier2 = unpack_from(f'{byteOrder}H', reader, offset=readOffset)[0]
            readOffset += 2            
            sphere_objects[i].Point1 = array(unpack_from(f'{byteOrder}3f', reader, offset=readOffset))
            readOffset += 12
            sphere_objects[i].Point2 = array(unpack_from(f'{byteOrder}3f', reader, offset=readOffset))
            readOffset += 12
            assert array_equal(sphere_objects[i].Point2, sphere_objects[i].Point1)
            sphere_objects[i].Radius = unpack_from(f'{byteOrder}f', reader, offset=readOffset)[0]
            readOffset += 4
            if sphere_objects[i].Radius < epsilon:
                sphere_objects[i].Radius = 0
            sphere_objects[i].IsSphere = True
        
        num_box_objects = unpack_from(f'{byteOrder}I', reader, offset=readOffset)[0]
        readOffset += 4
        
        box_objects = [self.CollisionObject() for _ in range(num_box_objects)]
        for i in range(num_box_objects):
            box_objects[i].Identifier1 = unpack_from(f'{byteOrder}H', reader, offset=readOffset)[0]
            readOffset += 2
            box_objects[i].Identifier2 = unpack_from(f'{byteOrder}H', reader, offset=readOffset)[0]
            readOffset += 2
            box_objects[i].Point1 = array(unpack_from(f'{byteOrder}3f', reader, offset=readOffset))
            readOffset += 12
            box_objects[i].Point2 = array(unpack_from(f'{byteOrder}3f', reader, offset=readOffset))
            readOffset += 12
            assert array_equal(box_objects[i].Point2, box_objects[i].Point1)
            box_objects[i].Size = array(unpack_from(f'{byteOrder}3f', reader, offset=readOffset))
            readOffset += 12
            box_objects[i].Size = [epsilon if x < epsilon else x for x in box_objects[i].Size]
            box_objects[i].Rotation = array(unpack_from(f'{byteOrder}3f', reader, offset=readOffset))
            readOffset += 12
            box_objects[i].BoxExtra = unpack_from(f'{byteOrder}9f', reader, offset=readOffset) #Always 0,0,1,0,0,0,0,1,0
            readOffset += 36
            
            assert array_equal(box_objects[i].BoxExtra, array((0.0, 0.0, 1.0, 0.0, 0.0, 0.0, 0.0, 1.0, 0.0)))
            
        unk = unpack_from(f'{byteOrder}I', reader, offset=readOffset)[0] #0 (maybe another object type). Never used in game
        assert unk == 0, (unk, hex(readOffset))
        readOffset += 4
        
        self.Objects: list[CsbFile.CollisionObject] = []
        
        # add both scene groups
        self.Objects.extend(sphere_objects)
        self.Objects.extend(box_objects)
        
        self.Unknown = unpack_from(f'{byteOrder}f', reader, offset=readOffset)[0] #unk (always 0)
        assert self.Unknown == 0, (self.Unknown, hex(readOffset))
        readOffset += 4
        readOffset += 16 #bytes of 0
        
        object_name_offsets = unpack_from(f'{byteOrder}{len(self.Objects)}I', reader, offset=readOffset)
        readOffset += (4 * len(self.Objects))
        object_flags = [None for _ in range(len(self.Objects))]
        
        for i in range(len(self.Objects)):
        # one of the first differences beyond endianness between the versions – I think sticker star is version 1 for the most part?
            if isVersion1:
                object_flags[i] = unpack_from(f'{byteOrder}I', reader, offset=readOffset)[0]
                readOffset += 4
            else:
                object_flags[i] = unpack_from(f'{byteOrder}Q', reader, offset=readOffset)[0]
                readOffset += 8
        
        object_indices = array(unpack_from(f'{byteOrder}{len(self.Objects)}H', reader, offset=readOffset))
        readOffset += (2 * len(self.Objects))
        
        object_string_table_length = unpack_from(f'{byteOrder}I', reader, offset=readOffset)[0]
        readOffset += 4
        object_string_table_pos = readOffset
        readOffset += object_string_table_length
        
        for i in range(len(self.Objects)):
            self.Objects[i].ColFlag = object_flags[i]
            self.Objects[i].NodeIndex = object_indices[i]
            
            self.Objects[i].Name = ReadZeroTerminatedString(reader, object_string_table_pos + object_name_offsets[i])
            #print(f"Object – {self.Objects[i].Name} – {self.Objects[i].NodeIndex}")
        
        
        num_meshes = unpack_from(f'{byteOrder}I', reader, offset=readOffset)[0]
        readOffset += 4
        
        name_offsets = unpack_from(f'{byteOrder}{num_meshes}I', reader, offset=readOffset)
        readOffset += (4 * num_meshes)
        tri_offsets = unpack_from(f'{byteOrder}{num_meshes}I', reader, offset=readOffset)
        readOffset += (4 * num_meshes)
        vert_offsets = unpack_from(f'{byteOrder}{num_meshes}I', reader, offset=readOffset)
        readOffset += (4 * num_meshes)
        
        flag_array = [None for _ in range(num_meshes)]
        for i in range(num_meshes):
            if isVersion1:
                flag_array[i] = unpack_from(f'{byteOrder}I', reader, offset=readOffset)[0]
                readOffset += 4
            else:
                flag_array[i] = unpack_from(f'{byteOrder}L', reader, offset=readOffset)[0]
                readOffset += 8
        
        attributes = unpack_from(f'{byteOrder}{num_meshes}I', reader, offset=readOffset)
        readOffset += (4 * num_meshes)
        
        #model data is later in the file
        
        #model_ids = unpack_from(f'{byteOrder}{num_meshes}I', reader, offset=readOffset)
        #readOffset += (4 * num_meshes)
        
        mesh_node_ids = unpack_from(f'{byteOrder}{num_meshes}H', reader, offset=readOffset)
        #print(mesh_node_ids)
        readOffset += (2 * num_meshes)
        #string table
        string_table_length = unpack_from(f'{byteOrder}I', reader, offset=readOffset)[0]
        readOffset += 4
        
        string_offset = readOffset
        readOffset += string_table_length
        
        num_nodes = unpack_from(f'{byteOrder}H', reader, offset=readOffset)[0]
        readOffset += 2
        available_node_ids = []
        negative_child_pos = []
        self.OldParenting = False
        for i in range(num_nodes):
            n = self.Node()
            n.ID = unpack_from(f'{byteOrder}H', reader, offset=readOffset)[0] #id
            readOffset += 2
            #print(f"Node – {n.ID}")
            n.Flags = unpack_from(f'{byteOrder}B', reader, offset=readOffset)[0] #flag
            readOffset += 1
            n.NumChildren = unpack_from(f'{byteOrder}b', reader, offset=readOffset)[0]
            #print(n.NumChildren)
            if n.NumChildren == -1:
                self.OldParenting = True
                negative_child_pos.append(i)
            else:
                available_node_ids.append(n.ID)
            readOffset += 1
            self.Nodes.append(n)
        #print(len(self.Nodes))
        
        meshes = [self.Mesh() for _ in range(num_meshes)]
        for i in range(num_meshes):
            meshes[i].MaterialAttribute = attributes[i]
            meshes[i].NodeIndex  = mesh_node_ids[i]
            
            if not meshes[i].NodeIndex in available_node_ids:
                movenode = self.Nodes[negative_child_pos[0]]
                self.Nodes.pop(negative_child_pos[0])
                negative_child_pos = [x - 1 for x in negative_child_pos]
                negative_child_pos.pop(0)
                self.Nodes.append(movenode)
                meshes[i].NodeIndex = movenode.ID
            
            meshes[i].ColFlag = flag_array[i]

            
            meshes[i].Name = ReadZeroTerminatedString(reader, string_offset + name_offsets[i])
            #print(f"Mesh – {meshes[i].Name}")
        #print([x.ID for x in self.Nodes])
        
        # go back and fix broken node ids for objects now that we now what nodes exist
        for i in range(len(self.Objects)):
            if not self.Objects[i].NodeIndex in available_node_ids:
                movenode = self.Nodes[negative_child_pos[0]]
                self.Nodes.pop(negative_child_pos[0])
                negative_child_pos = [x - 1 for x in negative_child_pos]
                negative_child_pos.pop(0)
                self.Nodes.append(movenode)
                self.Objects[i].NodeIndex = movenode.ID
        
        num_models = 1 # There is only 1 combined model – DEADBEEF
        
        #model group headers
        models: list[CsbFile.Model] = [self.Model() for _ in range(num_models)]
        for i in range(num_models):
            models[i].Unknown0 = unpack_from(f'{byteOrder}I', reader, offset=readOffset)[0] #=1 (3 in other titles)
            assert models[i].Unknown0 == 1, (models[i].Unknown0, hex(readOffset))
            readOffset += 4
            
            unk2 = unpack_from(f'{byteOrder}8s', reader, offset=readOffset)[0]
            readOffset += 8
            
            models[i].Name = ReadZeroTerminatedString(reader, readOffset)
            #print(f"Model – {models[i].Name}")
            
            # [...]
            readOffset += 64
            
            models[i].Unknown5 = unpack_from(f'{byteOrder}I', reader, offset=readOffset)[0]
            readOffset += 4
            
            models[i].NumVertices = unpack_from(f'{byteOrder}I', reader, offset=readOffset)[0]
            readOffset += 4
            models[i].NumTriangles = unpack_from(f'{byteOrder}I', reader, offset=readOffset)[0]
            readOffset += 4
            models[i].Zero = unpack_from(f'{byteOrder}3f', reader, offset=readOffset)
            readOffset += 12
            models[i].Translate = unpack_from(f'{byteOrder}3f', reader, offset=readOffset)
            readOffset += 12
            models[i].Rotation = unpack_from(f'{byteOrder}3f', reader, offset=readOffset)
            readOffset += 12
        
        self.Models.extend(models)
        
        for i in range(num_models):
            models[i].Bounding.Read(reader, readOffset, byteOrder)
            readOffset += 24
            
            positions = [None for _ in range(models[i].NumVertices)]
            
            for v in range(models[i].NumVertices):
                positions[v] = unpack_from(f'{byteOrder}3f', reader, offset=readOffset)
                readOffset += 12
            
            tris = [Triangle() for _ in range(models[i].NumTriangles)]
            for v in range(models[i].NumTriangles):
                tris[v].A = unpack_from(f'{byteOrder}I', reader, offset=readOffset)[0]
                readOffset += 4
                tris[v].B = unpack_from(f'{byteOrder}I', reader, offset=readOffset)[0]
                readOffset += 4
                tris[v].C = unpack_from(f'{byteOrder}I', reader, offset=readOffset)[0]
                readOffset += 4
                tris[v].Normal = unpack_from(f'{byteOrder}3f', reader, offset=readOffset)
                readOffset += 12
                tris[v].Vertices = [None, None, None]
                tris[v].Vertices[0] = positions[tris[v].A]
                tris[v].Vertices[1] = positions[tris[v].B]
                tris[v].Vertices[2] = positions[tris[v].C]
            models[i].Positions = positions.copy()
            models[i].Triangles = tris.copy()
            
            #DEADBEEF model has combined meshes
            #Typically paired with a .ctb file for searching collision with octrees
            
            for m in range(len(meshes)):
                #num of vertices and tris is next index – current
                tri_idx = tri_offsets[m]
                vtx_idx = vert_offsets[m]
                
                tri_end_idx = models[i].NumTriangles
                vtx_end_idx = models[i].NumVertices
                
                if m < len(meshes) - 1: 
                    if tri_offsets[m + 1] != models[i].NumTriangles:
                        tri_end_idx = tri_offsets[m + 1]
                    
                    if vert_offsets[m + 1] != models[i].NumVertices:
                        vtx_end_idx = vert_offsets[m + 1]
                
                if (tri_idx >= tri_end_idx or models[i].NumTriangles == 0):
                    continue
                
                num_verts = vtx_end_idx - vtx_idx
                num_tris = tri_end_idx - tri_idx
                
                meshes[m].NumVertices = num_verts
                meshes[m].NumTriangles = num_tris
                
                meshes[m].Positions = positions[vtx_idx : num_verts + vtx_idx].copy()
                meshes[m].Triangles = tris[tri_idx : num_tris + tri_idx].copy()
                for v in range(len(meshes[m].Triangles)):
                    meshes[m].Triangles[v].A -= vtx_idx
                    meshes[m].Triangles[v].B -= vtx_idx
                    meshes[m].Triangles[v].C -= vtx_idx
            models[i].Meshes.extend(meshes)
            
            readOffset += 4 # 0
            readOffset += 4 # 0
            
            num_split_models = unpack_from(f'{byteOrder}I', reader, offset=readOffset)[0]
            readOffset += 4
            self.SubModelBounding.Read(reader, readOffset, byteOrder)
            readOffset += 24
            
            models_split = [self.Model() for _ in range(num_split_models)]
            for i in range(num_split_models):
                models_split[i].Meshes = []
                models_split[i].Triangles = []
                models_split[i].Positions = []
                models_split[i].Unknown0 = unpack_from(f'{byteOrder}I', reader, offset=readOffset)[0] #Always 1
                assert models_split[i].Unknown0 == 1, (models_split[i].Unknown0, hex(readOffset))
                readOffset += 4
                models_split[i].NodeIndex = unpack_from(f'{byteOrder}H', reader, offset=readOffset)[0] #id
                
                if not models_split[i].NodeIndex in available_node_ids:
                    movenode = self.Nodes[negative_child_pos[0]]
                    self.Nodes.pop(negative_child_pos[0])
                    negative_child_pos = [x - 1 for x in negative_child_pos]
                    negative_child_pos.pop(0)
                    self.Nodes.append(movenode)
                    models_split[i].NodeIndex = movenode.ID
                
                readOffset += 2
                readOffset += 2 # 0
                
                if isVersion1:
                    models_split[i].ColFlag = unpack_from(f'{byteOrder}H', reader, offset=readOffset)[0]
                    readOffset += 2
                    models_split[i].MaterialAttribute = unpack_from(f'{byteOrder}H', reader, offset=readOffset)[0]
                    readOffset += 2
                else:
                    models_split[i].ColFlag = unpack_from(f'{byteOrder}L', reader, offset=readOffset)[0]
                    readOffset += 8
                    models_split[i].MaterialAttribute = unpack_from(f'{byteOrder}I', reader, offset=readOffset)[0]
                    readOffset += 4
                    models_split[i].Unknown4 = unpack_from(f'{byteOrder}I', reader, offset=readOffset)[0] #Always 4
                    assert models_split[i].Unknown4 == 4, (models_split[i].Unknown4, hex(readOffset))
                    readOffset += 4
                models_split[i].Name = ReadZeroTerminatedString(reader, readOffset)
                #print(f"Model Split – {models_split[i].Name}")
                
                #models_split[i].Unknown5 = unpack_from(f'{byteOrder}I', reader, offset=readOffset)[0] #Always 1
                #assert models_split[i].Unknown5 == 1, (models_split[i].Unknown5, hex(readOffset))
                #readOffset += 4
                
                # [...]
                readOffset += 64
                
                models_split[i].Unknown5 = unpack_from(f'{byteOrder}I', reader, offset=readOffset)[0]
                readOffset += 4
                
                #print(models_split[i].Name,hex(readOffset))
                #return
                models_split[i].NumVertices = unpack_from(f'{byteOrder}I', reader, offset=readOffset)[0]
                readOffset += 4
                models_split[i].NumTriangles = unpack_from(f'{byteOrder}I', reader, offset=readOffset)[0]
                readOffset += 4
                models_split[i].Zero = unpack_from(f'{byteOrder}3f', reader, offset=readOffset)
                readOffset += 12
                models_split[i].Translate = unpack_from(f'{byteOrder}3f', reader, offset=readOffset)
                readOffset += 12
                models_split[i].Rotation = unpack_from(f'{byteOrder}3f', reader, offset=readOffset)
                readOffset += 12
                models_split[i].Bounding.Read(reader, readOffset, byteOrder)
                readOffset += 24
                
                
                positions = [None for _ in range(models_split[i].NumVertices)]
                
                for v in range(models_split[i].NumVertices):
                    positions[v] = unpack_from(f'{byteOrder}3f', reader, offset=readOffset)
                    readOffset += 12
                
                tris = [Triangle() for _ in range(models_split[i].NumTriangles)]
                for v in range(models_split[i].NumTriangles):
                    tris[v].A = unpack_from(f'{byteOrder}I', reader, offset=readOffset)[0]
                    readOffset += 4
                    tris[v].B = unpack_from(f'{byteOrder}I', reader, offset=readOffset)[0]
                    readOffset += 4
                    tris[v].C = unpack_from(f'{byteOrder}I', reader, offset=readOffset)[0]
                    readOffset += 4
                    tris[v].Normal = unpack_from(f'{byteOrder}3f', reader, offset=readOffset)
                    readOffset += 12
                    
                    tris[v].Vertices = [None, None, None]
                    tris[v].Vertices[0] = positions[tris[v].A]
                    tris[v].Vertices[1] = positions[tris[v].B]
                    tris[v].Vertices[2] = positions[tris[v].C] 
                
                models_split[i].Positions = positions.copy()
                models_split[i].Triangles = tris.copy()
            self.Models.extend(models_split)
    
    def Write(self, bigEndian: bool) -> bytearray:
        
        def BuildStringTable(List: list[str]) -> bytearray:
            writer = bytearray()
            for Str in List:
                writer.extend(Str.encode('utf-8'))
                writer.extend(b'\x00') #zero terminate
            writer.extend(b'\x00' * ((4 - (len(writer) % 4)) % 4))
            return writer
                
        
        writer = bytearray()
        
        byteOrder = '>' if bigEndian else '<'
        
        isVersion1 = True
        
        sphere_objects = [obj for obj in self.Objects if obj.IsSphere]
        box_objects = [obj for obj in self.Objects if not obj.IsSphere]
        
        writer.extend(pack(f'{byteOrder}I', len(sphere_objects)))
        for group in sphere_objects:
            writer.extend(pack(f'{byteOrder}H', group.Identifier1))
            writer.extend(pack(f'{byteOrder}H', group.Identifier2))
            writer.extend(pack(f'{byteOrder}3f', *group.Point1))
            writer.extend(pack(f'{byteOrder}3f', *group.Point2))
            writer.extend(pack(f'{byteOrder}f', group.Radius))
        
        writer.extend(pack(f'{byteOrder}I', len(box_objects)))
        for group in box_objects:
            writer.extend(pack(f'{byteOrder}H', group.Identifier1))
            writer.extend(pack(f'{byteOrder}H', group.Identifier2))
            writer.extend(pack(f'{byteOrder}3f', *group.Point1))
            writer.extend(pack(f'{byteOrder}3f', *group.Point2))
            writer.extend(pack(f'{byteOrder}3f', *group.Size))
            writer.extend(pack(f'{byteOrder}3f', *group.Rotation))
            writer.extend(pack(f'{byteOrder}9f', *group.BoxExtra))
        
        writer.extend(pack(f'{byteOrder}I', 0)) #0 (maybe another object type)
        writer.extend(pack(f'{byteOrder}I', 0)) #0
        writer.extend(pack(f'{byteOrder}I', 0)) #0
        writer.extend(pack(f'{byteOrder}I', 0)) #0
        writer.extend(pack(f'{byteOrder}I', 0)) #0
        writer.extend(pack(f'{byteOrder}I', 0)) #0
        
        # reorder objects by type
        self.Objects = sphere_objects + box_objects
        
        #object name offsets
        object_name_offset = 0
        for group in self.Objects:
            writer.extend(pack(f'{byteOrder}I', object_name_offset))
            object_name_offset += len(group.Name) + 1
        
        for group in self.Objects:
            writer.extend(pack(f'{byteOrder}I', group.ColFlag))
        
        for group in self.Objects:
            writer.extend(pack(f'{byteOrder}H', group.NodeIndex))
        
        string_table = BuildStringTable([group.Name for group in self.Objects])
        writer.extend(pack(f'{byteOrder}I', len(string_table)))
        writer.extend(string_table)
        
        #Only select the first model 
        #Additional models don't use a combined buffer
        meshes = self.Models[0].Meshes
        
        writer.extend(pack(f'{byteOrder}I', len(meshes))) #mesh count
        
        #name offsets
        name_offset = 0
        for mesh in meshes:
            writer.extend(pack(f'{byteOrder}I', name_offset))
            name_offset += len(mesh.Name) + 1
        #triangle start indices
        tri_index = 0
        tri_start_indexes = []
        for mesh in meshes:
            writer.extend(pack(f'{byteOrder}I', tri_index))
            tri_start_indexes.append(tri_index)
            tri_index += mesh.NumTriangles
        #vertex start indices
        vtx_index = 0
        vtx_start_indexes = []
        for mesh in meshes:
            writer.extend(pack(f'{byteOrder}I', vtx_index))
            vtx_start_indexes.append(vtx_index)
            vtx_index += mesh.NumVertices
        #uint32 flags
        for mesh in meshes:
            writer.extend(pack(f'{byteOrder}I', mesh.ColFlag))
        #uint32 material attributes
        for mesh in meshes:
            writer.extend(pack(f'{byteOrder}I', mesh.MaterialAttribute))
        #node indices
        for mesh in meshes:
            writer.extend(pack(f'{byteOrder}H', mesh.NodeIndex))
        #build string table
        node_string_table = BuildStringTable([mesh.Name for mesh in meshes])
        writer.extend(pack(f'{byteOrder}I', len(node_string_table)))
        writer.extend(node_string_table)
        
        #nodes
        writer.extend(pack(f'{byteOrder}H', len(self.Nodes)))
        for node in self.Nodes:
            writer.extend(pack(f'{byteOrder}H', node.ID))
            writer.extend(pack(f'{byteOrder}B', node.Flags))
            writer.extend(pack(f'{byteOrder}b', node.NumChildren))
        
        writer.extend(pack(f'{byteOrder}I', 1))
        writer.extend(b'\x00\x00\x00\x00\x00\x00\x00\x00')
        for model in self.Models:
            if model.Name != 'DEADBEEF':
                writer.extend(pack(f'{byteOrder}I', model.Unknown0))
                writer.extend(pack(f'{byteOrder}I', model.NodeIndex))
                writer.extend(pack(f'{byteOrder}H', model.ColFlag))
                writer.extend(pack(f'{byteOrder}H', model.MaterialAttribute))
            
            writer.extend(model.Name.encode('utf-8'))
            writer.extend(b'\x00' * (64 - len(model.Name.encode('utf-8'))))
            writer.extend(pack(f'{byteOrder}I', model.Unknown5))
            writer.extend(pack(f'{byteOrder}I', model.NumVertices))
            writer.extend(pack(f'{byteOrder}I', model.NumTriangles))
            writer.extend(pack(f'{byteOrder}3f', *model.Zero))
            writer.extend(pack(f'{byteOrder}3f', *model.Translate))
            writer.extend(pack(f'{byteOrder}3f', *model.Rotation))
            writer.extend(pack(f'{byteOrder}6f', *model.Bounding.Min, *model.Bounding.Max))
            
            for pos in model.Positions:
                writer.extend(pack(f'{byteOrder}3f', *pos))
            for tri in model.Triangles:
                writer.extend(pack(f'{byteOrder}I', tri.A))
                writer.extend(pack(f'{byteOrder}I', tri.B))
                writer.extend(pack(f'{byteOrder}I', tri.C))
                writer.extend(pack(f'{byteOrder}3f', *tri.Normal))
            if model.Name == 'DEADBEEF': #DEADBEEF model where it has model list and total bounding of sub models
                writer.extend(pack(f'{byteOrder}I', 0))
                writer.extend(b'\x00\x00\x00\x00')
                writer.extend(pack(f'{byteOrder}I', len(self.Models) - 1))
                writer.extend(pack(f'{byteOrder}6f', *self.SubModelBounding.Min, *self.SubModelBounding.Max))
        return writer
    
    def __init__(self, stream: bytearray = None, bigEndian: bool = False):
        if not stream is None:
            self.Read(stream, bigEndian)
